package com.one.mini.service;

import com.one.mini.entity.Agent;
import com.one.mini.repository.AgentRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class AgentService {
    private final AgentRepository agentRepository;

    public List<Agent> getAllAgents() {
        return agentRepository.findAll();
    }

    public List<Agent> getAgentsByCategory(String category) {
        return agentRepository.findByCategory(category);
    }

    public Agent getAgentById(Long id) {
        return agentRepository.findById(id).orElse(null);
    }

    @Transactional
    public Agent createAgent(Agent agent) {
        return agentRepository.save(agent);
    }

    @Transactional
    public Agent updateAgent(Long id, Agent updates) {
        Agent agent = agentRepository.findById(id).orElse(null);
        if (agent == null) return null;

        if (updates.getName() != null) agent.setName(updates.getName());
        if (updates.getRole() != null) agent.setRole(updates.getRole());
        if (updates.getPosition() != null) agent.setPosition(updates.getPosition());
        if (updates.getAvatar() != null) agent.setAvatar(updates.getAvatar());
        if (updates.getStatus() != null) agent.setStatus(updates.getStatus());
        if (updates.getCurrentTask() != null) agent.setCurrentTask(updates.getCurrentTask());
        if (updates.getRecentOutput() != null) agent.setRecentOutput(updates.getRecentOutput());
        if (updates.getIsOnDuty() != null) agent.setIsOnDuty(updates.getIsOnDuty());
        if (updates.getSchedule() != null) agent.setSchedule(updates.getSchedule());
        if (updates.getCategory() != null) agent.setCategory(updates.getCategory());
        if (updates.getSkills() != null) agent.setSkills(updates.getSkills());
        if (updates.getTasksCompleted() != null) agent.setTasksCompleted(updates.getTasksCompleted());
        if (updates.getAccuracy() != null) agent.setAccuracy(updates.getAccuracy());
        if (updates.getAvgResponseTime() != null) agent.setAvgResponseTime(updates.getAvgResponseTime());
        if (updates.getPrompt() != null) agent.setPrompt(updates.getPrompt());

        return agentRepository.save(agent);
    }

    @Transactional
    public void deleteAgent(Long id) {
        agentRepository.deleteById(id);
    }
}