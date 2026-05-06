package com.one.mini;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class OneMiniApplication {
    public static void main(String[] args) {
        SpringApplication.run(OneMiniApplication.class, args);
    }
}