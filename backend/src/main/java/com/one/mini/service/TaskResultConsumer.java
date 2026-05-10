package com.one.mini.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.connection.stream.*;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import com.one.mini.entity.Task;
import com.one.mini.entity.TaskStep;
import com.one.mini.repository.TaskRepository;
import com.one.mini.repository.TaskStepRepository;

import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class TaskResultConsumer {

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    private final TaskRepository taskRepository;
    private final TaskStepRepository taskStepRepository;

    private static final String RESULT_STREAM = "agent:task:result";
    private static final String LOG_STREAM = "agent:log";
    private static final String CONSUMER_GROUP = "java-backend";
    private static final String CONSUMER_NAME = "backend-1";

    private volatile boolean groupInitialized = false;

    @Scheduled(fixedDelay = 2000, initialDelay = 5000)
    public void consumeResults() {
        try {
            ensureConsumerGroup();
            readAndProcessResults();
        } catch (Exception e) {
            log.error("Error consuming results: {}", e.getMessage());
        }
    }

    @Scheduled(fixedDelay = 5000, initialDelay = 10000)
    public void consumeLogs() {
        try {
            readAndProcessLogs();
        } catch (Exception e) {
            log.debug("Error consuming logs: {}", e.getMessage());
        }
    }

    private void ensureConsumerGroup() {
        if (groupInitialized) return;
        try {
            redisTemplate.opsForStream().createGroup(RESULT_STREAM, CONSUMER_GROUP);
            log.info("Created consumer group '{}' for stream '{}'", CONSUMER_GROUP, RESULT_STREAM);
            try {
                redisTemplate.opsForStream().createGroup(LOG_STREAM, CONSUMER_GROUP);
            } catch (Exception ignored) {
            }
            groupInitialized = true;
        } catch (Exception e) {
            if (e.getMessage() != null && e.getMessage().contains("BUSYGROUP")) {
                log.debug("Consumer group '{}' already exists", CONSUMER_GROUP);
                groupInitialized = true;
            } else {
                log.warn("Failed to create consumer group '{}': {}", CONSUMER_GROUP, e.getMessage());
                // Don't set groupInitialized — retry next cycle
            }
        }
    }

    private void readAndProcessResults() {
        Consumer consumer = Consumer.from(CONSUMER_GROUP, CONSUMER_NAME);
        StreamReadOptions options = StreamReadOptions.empty().count(10);

        try {
            // On first run, read all pending messages from stream start
            if (!groupInitialized) {
                List<MapRecord<String, Object, Object>> catchup = redisTemplate.opsForStream().read(
                        consumer,
                        options,
                        StreamOffset.create(RESULT_STREAM, ReadOffset.from("0-0"))
                );
                if (catchup != null && !catchup.isEmpty()) {
                    log.info("Catching up {} pending result messages", catchup.size());
                    processMessages(catchup);
                }
            }

            // Normal: read new messages
            List<MapRecord<String, Object, Object>> messages = redisTemplate.opsForStream().read(
                    consumer,
                    options,
                    StreamOffset.create(RESULT_STREAM, ReadOffset.lastConsumed())
            );
            processMessages(messages);
        } catch (Exception e) {
            log.debug("Error reading result stream: {}", e.getMessage());
        }
    }

    private void processMessages(List<MapRecord<String, Object, Object>> messages) {
        if (messages == null || messages.isEmpty()) return;

        for (MapRecord<String, Object, Object> message : messages) {
            try {
                String taskId = getStrValue(message, "task_id");
                String fromAgent = getStrValue(message, "from_agent");
                String status = getStrValue(message, "status");
                String resultJson = getStrValue(message, "result");

                if (taskId == null) continue;

                log.info("Processing result: taskId={}, fromAgent={}, status={}", taskId, fromAgent, status);
                processResult(taskId, fromAgent, status, resultJson);
            } catch (Exception e) {
                log.error("Error processing result message: {}", e.getMessage());
            }
        }
    }

    private String getStrValue(MapRecord<String, Object, Object> message, String key) {
        Object value = message.getValue().get(key);
        return value != null ? value.toString() : null;
    }

    private void processResult(String taskId, String fromAgent, String status, String resultJson) {
        Task task = taskRepository.findByTaskId(taskId).orElse(null);
        if (task == null) {
            log.warn("Task not found: taskId={}", taskId);
            return;
        }

        task.setStatus("completed".equals(status) ? "completed" : "failed");
        if (resultJson != null) {
            try {
                Object parsed = objectMapper.readValue(resultJson, Object.class);
                task.setOutputJson(objectMapper.writeValueAsString(parsed));
            } catch (Exception e) {
                task.setOutputJson(resultJson);
            }
        }
        taskRepository.save(task);
        log.info("Updated task {}: status={}", taskId, task.getStatus());

        List<TaskStep> steps = taskStepRepository.findByTaskId(taskId);
        TaskStep matchingStep = steps.stream()
                .filter(s -> fromAgent != null && fromAgent.equals(s.getAgentName()))
                .findFirst()
                .orElse(null);

        if (matchingStep == null) {
            try {
                matchingStep = taskStepRepository.findByTaskIdAndAgentName(taskId, fromAgent).orElse(null);
            } catch (Exception e) {
                log.debug("Could not find step by taskIdAndAgentName: {}", e.getMessage());
            }
        }

        if (matchingStep == null && !steps.isEmpty()) {
            matchingStep = steps.get(steps.size() - 1);
        }

        if (matchingStep != null) {
            matchingStep.setStatus("completed".equals(status) ? "completed" : "failed");
            if (resultJson != null) {
                try {
                    Object parsed = objectMapper.readValue(resultJson, Object.class);
                    matchingStep.setOutputJson(objectMapper.writeValueAsString(parsed));
                } catch (Exception e) {
                    matchingStep.setOutputJson(resultJson);
                }
            }
            taskStepRepository.save(matchingStep);
            log.info("Updated step {}: agentName={}, status={}", matchingStep.getId(), matchingStep.getAgentName(), matchingStep.getStatus());
        }

        if ("product_picker".equals(fromAgent) && "completed".equals(status)) {
            log.info("Product picker completed for task {}, finance analyst will be triggered by AI engine auto-chain", taskId);
        }
    }

    private void readAndProcessLogs() {
        Consumer consumer = Consumer.from(CONSUMER_GROUP, CONSUMER_NAME + "-logs");
        StreamReadOptions options = StreamReadOptions.empty().count(20);

        try {
            List<MapRecord<String, Object, Object>> messages = redisTemplate.opsForStream().read(
                    consumer,
                    options,
                    StreamOffset.create(LOG_STREAM, ReadOffset.lastConsumed())
            );

            if (messages == null || messages.isEmpty()) return;

            for (MapRecord<String, Object, Object> message : messages) {
                try {
                    String taskId = message.getValue().get("task_id") != null ? message.getValue().get("task_id").toString() : null;
                    String agentName = message.getValue().get("agent_name") != null ? message.getValue().get("agent_name").toString() : null;
                    String level = message.getValue().get("level") != null ? message.getValue().get("level").toString() : null;
                    String logMessage = message.getValue().get("message") != null ? message.getValue().get("message").toString() : null;

                    if (taskId != null) {
                        log.info("[AI Engine Log] taskId={}, agent={}, level={}: {}", taskId, agentName, level, logMessage);
                    }
                } catch (Exception e) {
                    log.debug("Error processing log message: {}", e.getMessage());
                }
            }
        } catch (Exception e) {
            log.debug("Error reading log stream: {}", e.getMessage());
        }
    }
}