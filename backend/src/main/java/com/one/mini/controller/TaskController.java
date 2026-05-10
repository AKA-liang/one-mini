package com.one.mini.controller;

import com.one.mini.entity.Task;
import com.one.mini.entity.TaskStep;
import com.one.mini.service.TaskService;
import com.one.mini.service.MessageBusService;
import com.one.mini.repository.TaskRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/tasks")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class TaskController {
    private final TaskService taskService;
    private final MessageBusService messageBusService;
    private final ObjectMapper objectMapper;
    private final TaskRepository taskRepository;

    @PostMapping
    public Task createTask(@RequestBody Map<String, Object> body) {
        String type = (String) body.getOrDefault("type", "product_analysis");
        Object input = body.get("inputJson");
        String inputJson = "{}";
        if (input != null) {
            try {
                inputJson = objectMapper.writeValueAsString(input);
            } catch (Exception e) {
                inputJson = input.toString();
            }
        }

        Task task = taskService.createTask(type, inputJson);

        String toAgent = "product_picker";
        if ("finance_review".equals(type)) {
            toAgent = "finance_analyst";
        } else if (type.startsWith("comment_") || type.startsWith("publish_")
                   || "douyin_operator".equals(type)) {
            toAgent = "douyin_operator";
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> payload = body.get("inputJson") instanceof Map
                ? (Map<String, Object>) body.get("inputJson")
                : Map.of("raw", inputJson);

        String msgId = messageBusService.sendTask(task.getTaskId(), toAgent, type, payload);
        if (msgId == null) {
            task = taskService.updateTaskStatus(task.getTaskId(), "failed");
            task.setOutputJson("{\"error\":\"Redis unavailable — task could not be sent\"}");
            taskRepository.save(task);
            return task;
        }

        TaskStep step = taskService.createTaskStep(task.getTaskId(), toAgent, inputJson);
        task = taskService.updateTaskStatus(task.getTaskId(), "running");

        return task;
    }

    @GetMapping
    public List<Task> listTasks(@RequestParam(required = false) String type,
                                @RequestParam(required = false) String status) {
        if (type != null) return taskService.getTasksByType(type);
        if (status != null) return taskService.getTasksByStatus(status);
        return taskService.getAllTasks();
    }

    @GetMapping("/{taskId}")
    public ResponseEntity<Task> getTask(@PathVariable String taskId) {
        Task task = taskService.getTaskByTaskId(taskId);
        if (task == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(task);
    }

    @GetMapping("/{taskId}/steps")
    public List<TaskStep> getTaskSteps(@PathVariable String taskId) {
        return taskService.getTaskSteps(taskId);
    }
}