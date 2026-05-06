package com.one.mini.repository;

import com.one.mini.entity.TaskStep;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TaskStepRepository extends JpaRepository<TaskStep, Long> {
    List<TaskStep> findByTaskId(String taskId);
    Optional<TaskStep> findByTaskIdAndAgentName(String taskId, String agentName);
}