/*
 * AdminController.java —— Web 管理端接口（需 ADMIN 角色）
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：用户增删改查/重置密码；任务记录查询/删除；统计卡片。
 */
package com.zongshe3.track.controller;

import com.zongshe3.track.common.Result;
import com.zongshe3.track.pojo.User;
import com.zongshe3.track.service.TaskService;
import com.zongshe3.track.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
public class AdminController {

    private final UserService userService;
    private final TaskService taskService;

    // ---------------- 用户管理 ----------------

    @GetMapping("/users")
    public Result<Object> users(@RequestParam(required = false) String keyword,
                                @RequestParam(defaultValue = "1") int page,
                                @RequestParam(defaultValue = "10") int size) {
        return Result.ok(userService.pageUsers(keyword, page, size));
    }

    @PostMapping("/user")
    public Result<User> addUser(@RequestBody Map<String, String> body) {
        return Result.ok(userService.addByAdmin(
                body.get("username"), body.get("password"),
                body.get("nickname"), body.get("role")));
    }

    @PutMapping("/user/{id}/reset")
    public Result<Void> reset(@PathVariable Long id,
                              @RequestBody Map<String, String> body) {
        userService.resetPassword(id, body.get("password"));
        return Result.ok();
    }

    @DeleteMapping("/user/{id}")
    public Result<Void> deleteUser(@PathVariable Long id) {
        userService.deleteUser(id);
        return Result.ok();
    }

    // ---------------- 任务记录管理 ----------------

    @GetMapping("/tasks")
    public Result<Object> tasks(@RequestParam(required = false) String status,
                                @RequestParam(defaultValue = "1") int page,
                                @RequestParam(defaultValue = "10") int size) {
        return Result.ok(taskService.adminTasks(status, page, size));
    }

    @DeleteMapping("/task/{id}")
    public Result<Void> deleteTask(@PathVariable Long id) {
        taskService.deleteTask(id);
        return Result.ok();
    }

    @GetMapping("/stats")
    public Result<Object> stats() {
        return Result.ok(taskService.stats());
    }
}
