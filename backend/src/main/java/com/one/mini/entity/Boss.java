package com.one.mini.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "boss")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Boss {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(length = 200)
    private String position;

    @Column(length = 200)
    private String email;

    @Column(length = 50)
    private String phone;

    @Column(length = 200)
    private String department;

    @Column(length = 500)
    private String bio;

    @Column(length = 500)
    private String avatar;

    @Column(length = 20)
    private String joinDate;

    @Column(length = 50)
    private String efficiency;

    @Column(name = "team_size")
    private Integer teamSize;

    @Column(name = "projects_completed")
    private Integer projectsCompleted;

    @CreationTimestamp
    @Column(name = "create_time", updatable = false)
    private LocalDateTime createTime;

    @UpdateTimestamp
    @Column(name = "update_time")
    private LocalDateTime updateTime;
}