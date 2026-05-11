package com.one.mini.service;

import com.one.mini.entity.Task;
import com.one.mini.repository.TaskRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Slf4j
@Service
@RequiredArgsConstructor
public class TaskTimeoutService {

    private final TaskRepository taskRepository;

    /**
     * Every 60 seconds, mark running tasks older than 5 minutes as failed.
     */
    @Transactional
    @Scheduled(fixedRate = 60_000)
    public void failStaleRunningTasks() {
        LocalDateTime cutoff = LocalDateTime.now().minusMinutes(5);
        int count = taskRepository.failStaleRunningTasks(
                "failed",
                "{\"error\":\"task timed out — engine did not complete within 5 minutes\"}",
                cutoff
        );
        if (count > 0) {
            log.warn("Marked {} stale running tasks as failed (cutoff: {})", count, cutoff);
        }
    }
}
