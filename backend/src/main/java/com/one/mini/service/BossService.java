package com.one.mini.service;

import com.one.mini.entity.Boss;
import com.one.mini.repository.BossRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class BossService {
    private final BossRepository bossRepository;

    public Boss getBoss() {
        List<Boss> bosses = bossRepository.findAll();
        if (bosses.isEmpty()) {
            Boss defaultBoss = new Boss();
            defaultBoss.setName("张总");
            defaultBoss.setPosition("智能体控制中心负责人");
            defaultBoss.setEmail("boss@company.com");
            defaultBoss.setPhone("138-0013-8000");
            defaultBoss.setDepartment("AI运营中心");
            defaultBoss.setBio("致力于打造最优秀的AI数字员工团队，推动企业智能化转型");
            defaultBoss.setAvatar("");
            defaultBoss.setJoinDate("2024-01-15");
            defaultBoss.setTeamSize(13);
            defaultBoss.setProjectsCompleted(48);
            defaultBoss.setEfficiency("98.5%");
            return bossRepository.save(defaultBoss);
        }
        return bosses.get(0);
    }

    @Transactional
    public Boss updateBoss(Boss updates) {
        Boss boss = getBoss();
        if (updates.getName() != null) boss.setName(updates.getName());
        if (updates.getPosition() != null) boss.setPosition(updates.getPosition());
        if (updates.getEmail() != null) boss.setEmail(updates.getEmail());
        if (updates.getPhone() != null) boss.setPhone(updates.getPhone());
        if (updates.getDepartment() != null) boss.setDepartment(updates.getDepartment());
        if (updates.getBio() != null) boss.setBio(updates.getBio());
        if (updates.getAvatar() != null) boss.setAvatar(updates.getAvatar());
        if (updates.getJoinDate() != null) boss.setJoinDate(updates.getJoinDate());
        if (updates.getTeamSize() != null) boss.setTeamSize(updates.getTeamSize());
        if (updates.getProjectsCompleted() != null) boss.setProjectsCompleted(updates.getProjectsCompleted());
        if (updates.getEfficiency() != null) boss.setEfficiency(updates.getEfficiency());
        return bossRepository.save(boss);
    }
}