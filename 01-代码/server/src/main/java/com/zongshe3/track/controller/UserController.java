/*
 * UserController.java —— 小程序端用户功能接口
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：GET /api/user/info 个人信息；PUT /api/user/password 修改密码。
 */
package com.zongshe3.track.controller;

import com.zongshe3.track.common.Result;
import com.zongshe3.track.pojo.User;
import com.zongshe3.track.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/user")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @GetMapping("/info")
    public Result<User> info(@RequestAttribute("uid") Long uid) {
        return Result.ok(userService.info(uid));
    }

    @PutMapping("/password")
    public Result<Void> changePassword(@RequestAttribute("uid") Long uid,
                                       @RequestBody Map<String, String> body) {
        userService.changePassword(uid, body.get("oldPassword"), body.get("newPassword"));
        return Result.ok();
    }
}
