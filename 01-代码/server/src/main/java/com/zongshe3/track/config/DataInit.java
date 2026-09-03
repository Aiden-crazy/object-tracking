/*
 * DataInit.java —— 启动数据初始化
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：应用启动后检查默认管理员账号 admin/123456 是否存在，不存在则创建，
 *           保证 init.sql 执行后无需手工插管理员即可登录管理端。
 */
package com.zongshe3.track.config;

import com.zongshe3.track.mapper.UserMapper;
import com.zongshe3.track.pojo.User;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class DataInit implements CommandLineRunner {

    private final UserMapper userMapper;

    @Override
    public void run(String... args) {
        if (userMapper.findByUsername("admin") == null) {
            User admin = new User();
            admin.setUsername("admin");
            admin.setPassword(new BCryptPasswordEncoder().encode("123456"));
            admin.setNickname("系统管理员");
            admin.setRole("ADMIN");
            userMapper.insert(admin);
            log.info("已创建默认管理员账号 admin / 123456");
        }
    }
}
