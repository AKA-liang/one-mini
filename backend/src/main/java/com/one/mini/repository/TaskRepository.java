package com.one.mini.repository;

import com.one.mini.entity.Task;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface TaskRepository extends JpaRepository<Task, Long> {
    Optional<Task> findByTaskId(String taskId);
    List<Task> findByType(String type);
    List<Task> findByStatus(String status);
    List<Task> findByTypeAndStatus(String type, String status);

    List<Task> findByStatusAndCreateTimeBefore(String status, LocalDateTime cutoff);

    @Modifying
    @Query("UPDATE Task t SET t.status = :status, t.outputJson = :outputJson WHERE t.status = 'running' AND t.createTime < :cutoff")
    int failStaleRunningTasks(String status, String outputJson, LocalDateTime cutoff);
}