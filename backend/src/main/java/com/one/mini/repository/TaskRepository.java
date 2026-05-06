package com.one.mini.repository;

import com.one.mini.entity.Task;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface TaskRepository extends JpaRepository<Task, Long> {
    Optional<Task> findByTaskId(String taskId);
    List<Task> findByType(String type);
    List<Task> findByStatus(String status);
    List<Task> findByTypeAndStatus(String type, String status);
}