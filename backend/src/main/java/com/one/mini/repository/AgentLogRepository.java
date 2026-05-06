package com.one.mini.repository;

import com.one.mini.entity.AgentLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AgentLogRepository extends JpaRepository<AgentLog, Long> {
    List<AgentLog> findByTaskId(String taskId);
    List<AgentLog> findByAgentName(String agentName);
    List<AgentLog> findByTaskIdOrderByCreateTimeDesc(String taskId);
}