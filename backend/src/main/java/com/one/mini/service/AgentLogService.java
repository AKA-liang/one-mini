package com.one.mini.service;

import com.one.mini.entity.AgentLog;
import com.one.mini.repository.AgentLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class AgentLogService {
    private final AgentLogRepository agentLogRepository;

    public AgentLog log(String taskId, String agentName, String action, String level, String message) {
        AgentLog logEntry = new AgentLog();
        logEntry.setTaskId(taskId);
        logEntry.setAgentName(agentName);
        logEntry.setAction(action);
        logEntry.setLevel(level);
        logEntry.setMessage(message);
        return agentLogRepository.save(logEntry);
    }

    public List<AgentLog> getLogsByTaskId(String taskId) {
        return agentLogRepository.findByTaskIdOrderByCreateTimeDesc(taskId);
    }

    public List<AgentLog> getLogsByAgentName(String agentName) {
        return agentLogRepository.findByAgentName(agentName);
    }

    public List<AgentLog> getAllLogs() {
        return agentLogRepository.findAll();
    }
}