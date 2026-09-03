/*
 * TrackApplication.java —— 综合实践III《单目标跟踪系统》Web 后端启动类
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：Spring Boot 启动入口；扫描 Mapper 接口。
 */
package com.zongshe3.track;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.zongshe3.track.mapper")
public class TrackApplication {

    public static void main(String[] args) {
        SpringApplication.run(TrackApplication.class, args);
        System.out.println("综合实践III 单目标跟踪系统 Web后端启动成功: http://localhost:8080/admin.html");
    }
}
