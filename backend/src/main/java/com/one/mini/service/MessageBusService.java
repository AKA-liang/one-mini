package com.one.mini.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.connection.stream.StreamRecords;
import org.springframework.data.redis.connection.stream.StringRecord;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class MessageBusService {
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    private static final String TASK_STREAM = "agent:task";
    private static final String RESULT_STREAM = "agent:task:result";
    private static final String LOG_STREAM = "agent:log";
    private static final String COMMAND_STREAM = "agent:command";

    public String sendTask(String taskId, String toAgent, String action, Map<String, Object> payload) {
        try {
            Map<String, String> message = new HashMap<>();
            message.put("msg_id", java.util.UUID.randomUUID().toString());
            message.put("task_id", taskId);
            message.put("from_agent", "java_gateway");
            message.put("to_agent", toAgent);
            message.put("action", action);
            message.put("payload", objectMapper.writeValueAsString(payload));
            message.put("timestamp", Instant.now().toString());

            StringRecord record = StreamRecords.string(message).withStreamKey(TASK_STREAM);
            var result = redisTemplate.opsForStream().add(record);
            log.info("Sent task to {}: taskId={}, action={}", toAgent, taskId, action);
            return result != null ? result.getValue() : null;
        } catch (Exception e) {
            log.error("Failed to send task message: {}", e.getMessage());
            return null;
        }
    }

    public String sendResult(String taskId, String fromAgent, String status, Map<String, Object> result) {
        try {
            Map<String, String> message = new HashMap<>();
            message.put("task_id", taskId);
            message.put("from_agent", fromAgent);
            message.put("status", status);
            message.put("result", objectMapper.writeValueAsString(result));
            message.put("timestamp", Instant.now().toString());

            StringRecord record = StreamRecords.string(message).withStreamKey(RESULT_STREAM);
            var response = redisTemplate.opsForStream().add(record);
            log.info("Sent result from {}: taskId={}, status={}", fromAgent, taskId, status);
            return response != null ? response.getValue() : null;
        } catch (Exception e) {
            log.error("Failed to send result message: {}", e.getMessage());
            return null;
        }
    }

    public void sendLog(String taskId, String agentName, String level, String message) {
        try {
            Map<String, String> logMsg = new HashMap<>();
            logMsg.put("task_id", taskId);
            logMsg.put("agent_name", agentName);
            logMsg.put("level", level);
            logMsg.put("message", message);
            logMsg.put("timestamp", Instant.now().toString());

            StringRecord record = StreamRecords.string(logMsg).withStreamKey(LOG_STREAM);
            redisTemplate.opsForStream().add(record);
        } catch (Exception e) {
            log.error("Failed to send log message: {}", e.getMessage());
        }
    }
}