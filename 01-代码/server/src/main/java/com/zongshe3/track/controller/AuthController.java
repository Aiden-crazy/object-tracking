/*
 * AuthController.java —— 认证接口（小程序/管理端共用）
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：POST /api/auth/register 注册；POST /api/auth/login 登录（返回 JWT）。
 */
package com.zongshe3.track.controller;

import com.zongshe3.track.common.Result;
import com.zongshe3.track.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserService userService;

    @PostMapping("/register")
    public Result<Object> register(@RequestBody Map<String, String> body) {
        return Result.ok(userService.register(
                body.get("username"), body.get("password"), body.get("nickname")));
    }

    @PostMapping("/login")
    public Result<Object> login(@RequestBody Map<String, String> body) {
        return Result.ok(userService.login(body.get("username"), body.get("password")));
    }
}
