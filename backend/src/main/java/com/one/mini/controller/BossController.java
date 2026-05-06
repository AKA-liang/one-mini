package com.one.mini.controller;

import com.one.mini.entity.Boss;
import com.one.mini.service.BossService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/boss")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class BossController {
    private final BossService bossService;

    @GetMapping
    public Boss getBoss() {
        return bossService.getBoss();
    }

    @PostMapping
    public Boss updateBoss(@RequestBody Boss updates) {
        return bossService.updateBoss(updates);
    }

    @PutMapping
    public Boss updateBossInfo(@RequestBody Boss updates) {
        return bossService.updateBoss(updates);
    }
}