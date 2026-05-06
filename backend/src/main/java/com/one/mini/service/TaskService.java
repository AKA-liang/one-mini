package com.one.mini.service;

import com.one.mini.entity.Task;
import com.one.mini.entity.TaskStep;
import com.one.mini.repository.TaskRepository;
import com.one.mini.repository.TaskStepRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class TaskService {
    private final TaskRepository taskRepository;
    private final TaskStepRepository taskStepRepository;

    public List<Task> getAllTasks() {
        return taskRepository.findAll();
    }

    public List<Task> getTasksByType(String type) {
        return taskRepository.findByType(type);
    }

    public List<Task> getTasksByStatus(String status) {
        return taskRepository.findByStatus(status);
    }

    public Task getTaskByTaskId(String taskId) {
        return taskRepository.findByTaskId(taskId).orElse(null);
    }

    @Transactional
    public Task createTask(String type, String inputJson) {
        Task task = new Task();
        task.setTaskId(UUID.randomUUID().toString());
        task.setTraceId(UUID.randomUUID().toString());
        task.setType(type);
        task.setStatus("pending");
        task.setInputJson(inputJson);
        return taskRepository.save(task);
    }

    @Transactional
    public Task updateTaskStatus(String taskId, String status) {
        Task task = getTaskByTaskId(taskId);
        if (task == null) return null;
        task.setStatus(status);
        return taskRepository.save(task);
    }

    @Transactional
    public Task updateTaskOutput(String taskId, String outputJson) {
        Task task = getTaskByTaskId(taskId);
        if (task == null) return null;
        task.setOutputJson(outputJson);
        return taskRepository.save(task);
    }

    @Transactional
    public TaskStep createTaskStep(String taskId, String agentName, String inputJson) {
        TaskStep step = new TaskStep();
        step.setTaskId(taskId);
        step.setAgentName(agentName);
        step.setStatus("pending");
        step.setInputJson(inputJson);
        return taskStepRepository.save(step);
    }

    @Transactional
    public TaskStep updateStepStatus(Long stepId, String status, String outputJson, String errorMessage) {
        TaskStep step = taskStepRepository.findById(stepId).orElse(null);
        if (step == null) return null;
        step.setStatus(status);
        if (outputJson != null) step.setOutputJson(outputJson);
        if (errorMessage != null) step.setErrorMessage(errorMessage);
        return taskStepRepository.save(step);
    }

    public List<TaskStep> getTaskSteps(String taskId) {
        return taskStepRepository.findByTaskId(taskId);
    }
}