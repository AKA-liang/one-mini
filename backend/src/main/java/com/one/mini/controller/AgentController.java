package com.one.mini.controller;

import com.one.mini.entity.Agent;
import com.one.mini.service.AgentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/agents")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class AgentController {
    private final AgentService agentService;

    @GetMapping
    public List<Agent> getAllAgents(@RequestParam(required = false) String category) {
        if (category != null && !category.isEmpty()) {
            return agentService.getAgentsByCategory(category);
        }
        return agentService.getAllAgents();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Agent> getAgentById(@PathVariable Long id) {
        Agent agent = agentService.getAgentById(id);
        if (agent == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(agent);
    }

    @PostMapping
    public Agent createAgent(@RequestBody Agent agent) {
        return agentService.createAgent(agent);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Agent> updateAgent(@PathVariable Long id, @RequestBody Agent updates) {
        Agent updated = agentService.updateAgent(id, updates);
        if (updated == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteAgent(@PathVariable Long id) {
        agentService.deleteAgent(id);
        return ResponseEntity.ok().build();
    }
}