/*
 * UserService.java —— 用户与认证业务逻辑
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：注册(用户名唯一校验)、登录(BCrypt 校验+签发 JWT)、
 *           修改密码(校验旧密码)、管理端 用户增/删/重置密码/分页查询。
 */
package com.zongshe3.track.service;

import com.zongshe3.track.common.BizException;
import com.zongshe3.track.common.JwtUtil;
import com.zongshe3.track.mapper.TaskMapper;
import com.zongshe3.track.mapper.UserMapper;
import com.zongshe3.track.pojo.User;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserMapper userMapper;
    private final TaskMapper taskMapper;
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

    // ---------------- 小程序端用户功能 ----------------

    /** 注册（默认普通用户角色 USER） */
    public User register(String username, String password, String nickname) {
        if (username == null || username.trim().isEmpty()
                || password == null || password.length() < 6) {
            throw new BizException("用户名不能为空，密码长度不能少于6位");
        }
        if (userMapper.findByUsername(username.trim()) != null) {
            throw new BizException("用户名已被注册，请更换");
        }
        User u = new User();
        u.setUsername(username.trim());
        u.setPassword(encoder.encode(password));
        u.setNickname(nickname == null || nickname.isEmpty() ? username.trim() : nickname);
        u.setRole("USER");
        userMapper.insert(u);
        u.setPassword(null);
        return u;
    }

    /** 登录：成功返回 {token, user} */
    public Map<String, Object> login(String username, String password) {
        User u = userMapper.findByUsername(username == null ? "" : username.trim());
        if (u == null || !encoder.matches(password == null ? "" : password, u.getPassword())) {
            throw new BizException(401, "用户名或密码错误");
        }
        String token = JwtUtil.createToken(u.getId(), u.getUsername(), u.getRole());
        u.setPassword(null);
        Map<String, Object> data = new HashMap<>();
        data.put("token", token);
        data.put("user", u);
        return data;
    }

    /** 修改密码：需校验旧密码 */
    public void changePassword(Long uid, String oldPwd, String newPwd) {
        User u = userMapper.findById(uid);
        if (u == null) {
            throw new BizException(401, "用户不存在");
        }
        if (!encoder.matches(oldPwd == null ? "" : oldPwd, u.getPassword())) {
            throw new BizException("原密码错误");
        }
        if (newPwd == null || newPwd.length() < 6) {
            throw new BizException("新密码长度不能少于6位");
        }
        userMapper.updatePassword(uid, encoder.encode(newPwd));
    }

    public User info(Long uid) {
        User u = userMapper.findById(uid);
        if (u == null) {
            throw new BizException(401, "用户不存在");
        }
        u.setPassword(null);
        return u;
    }

    // ---------------- 管理端用户管理 ----------------

    public Map<String, Object> pageUsers(String keyword, int page, int size) {
        page = Math.max(page, 1);
        size = Math.min(Math.max(size, 1), 100);
        List<User> list = userMapper.pageUsers(keyword, (page - 1) * size, size);
        list.forEach(u -> u.setPassword(null));
        Map<String, Object> data = new HashMap<>();
        data.put("total", userMapper.countUsers(keyword));
        data.put("list", list);
        return data;
    }

    /** 管理端新增用户（可指定角色） */
    public User addByAdmin(String username, String password, String nickname, String role) {
        String r = ("ADMIN".equalsIgnoreCase(role)) ? "ADMIN" : "USER";
        if (username == null || username.trim().isEmpty() || password == null || password.length() < 6) {
            throw new BizException("用户名不能为空，密码长度不能少于6位");
        }
        if (userMapper.findByUsername(username.trim()) != null) {
            throw new BizException("用户名已存在");
        }
        User u = new User();
        u.setUsername(username.trim());
        u.setPassword(encoder.encode(password));
        u.setNickname(nickname == null || nickname.isEmpty() ? username.trim() : nickname);
        u.setRole(r);
        userMapper.insert(u);
        u.setPassword(null);
        return u;
    }

    /** 管理端重置密码 */
    public void resetPassword(Long id, String newPwd) {
        if (newPwd == null || newPwd.length() < 6) {
            throw new BizException("新密码长度不能少于6位");
        }
        if (userMapper.findById(id) == null) {
            throw new BizException("用户不存在");
        }
        userMapper.updatePassword(id, encoder.encode(newPwd));
    }

    /** 管理端删除用户：级联删除其任务记录 */
    @Transactional
    public void deleteUser(Long id) {
        if (userMapper.findById(id) == null) {
            throw new BizException("用户不存在");
        }
        taskMapper.deleteByUserId(id);
        userMapper.deleteById(id);
    }
}
