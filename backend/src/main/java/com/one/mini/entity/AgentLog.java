package com.one.mini.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "agent_log")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AgentLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "task_id", length = 64)
    private String taskId;

    @Column(name = "agent_name", length = 50)
    private String agentName;

    @Column(length = 100)
    private String action;

    @Column(length = 10)
    private String level = "info";

    @Column(columnDefinition = "TEXT")
    private String message;

    @CreationTimestamp
    @Column(name = "create_time", updatable = false)
    private LocalDateTime createTime;
}