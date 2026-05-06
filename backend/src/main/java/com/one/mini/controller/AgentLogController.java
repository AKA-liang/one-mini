package com.one.mini.controller;

import com.one.mini.entity.AgentLog;
import com.one.mini.service.AgentLogService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/agent-logs")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class AgentLogController {
    private final AgentLogService agentLogService;

    @GetMapping
    public List<AgentLog> getLogs(@RequestParam(required = false) String taskId,
                                  @RequestParam(required = false) String agentName) {
        if (taskId != null) return agentLogService.getLogsByTaskId(taskId);
        if (agentName != null) return agentLogService.getLogsByAgentName(agentName);
        return agentLogService.getAllLogs();
    }
}