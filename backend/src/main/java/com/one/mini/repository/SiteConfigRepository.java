package com.one.mini.repository;

import com.one.mini.entity.SiteConfig;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SiteConfigRepository extends JpaRepository<SiteConfig, Long> {
}