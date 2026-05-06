package com.one.mini.service;

import com.one.mini.entity.SiteConfig;
import com.one.mini.repository.SiteConfigRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class SiteConfigService {
    private final SiteConfigRepository siteConfigRepository;

    public SiteConfig getSiteConfig() {
        List<SiteConfig> configs = siteConfigRepository.findAll();
        if (configs.isEmpty()) {
            SiteConfig defaultConfig = new SiteConfig();
            defaultConfig.setSiteName("One Mini");
            defaultConfig.setSiteSubtitle("智能体控制中心");
            defaultConfig.setTotalEmployees(13);
            defaultConfig.setOnlineEmployees(13);
            return siteConfigRepository.save(defaultConfig);
        }
        return configs.get(0);
    }

    @Transactional
    public SiteConfig updateSiteConfig(SiteConfig updates) {
        SiteConfig config = getSiteConfig();
        if (updates.getSiteName() != null) config.setSiteName(updates.getSiteName());
        if (updates.getSiteSubtitle() != null) config.setSiteSubtitle(updates.getSiteSubtitle());
        if (updates.getTotalEmployees() != null) config.setTotalEmployees(updates.getTotalEmployees());
        if (updates.getOnlineEmployees() != null) config.setOnlineEmployees(updates.getOnlineEmployees());
        return siteConfigRepository.save(config);
    }
}