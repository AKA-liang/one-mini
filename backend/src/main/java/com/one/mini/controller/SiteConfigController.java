package com.one.mini.controller;

import com.one.mini.entity.SiteConfig;
import com.one.mini.service.SiteConfigService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/site-config")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class SiteConfigController {
    private final SiteConfigService siteConfigService;

    @GetMapping
    public SiteConfig getSiteConfig() {
        return siteConfigService.getSiteConfig();
    }

    @PostMapping
    public SiteConfig updateSiteConfig(@RequestBody SiteConfig updates) {
        return siteConfigService.updateSiteConfig(updates);
    }
}