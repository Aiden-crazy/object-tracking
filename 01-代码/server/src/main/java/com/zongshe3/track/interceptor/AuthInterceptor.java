/*
 * AuthInterceptor.java —— JWT 认证与角色鉴权拦截器
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：拦截 /api/** 请求，校验 Authorization: Bearer <token>，
 *           将 uid/username/role 写入 request 属性；/api/admin/** 要求 ADMIN 角色。
 */
package com.zongshe3.track.interceptor;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.zongshe3.track.common.JwtUtil;
import com.zongshe3.track.common.Result;
import io.jsonwebtoken.Claims;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class AuthInterceptor implements HandlerInterceptor {

    private final ObjectMapper mapper = new ObjectMapper();

    @Override
    public boolean preHandle(HttpServletRequest req, HttpServletResponse resp,
                             Object handler) throws Exception {
        // 放行 OPTIONS 预检
        if ("OPTIONS".equalsIgnoreCase(req.getMethod())) {
            return true;
        }
        String auth = req.getHeader("Authorization");
        String token = (auth != null && auth.startsWith("Bearer "))
                ? auth.substring(7) : null;
        if (token == null || token.isBlank()) {
            return deny(resp, 401, "未登录或登录已过期");
        }
        try {
            Claims claims = JwtUtil.parse(token);
            Long uid = claims.get("uid", Long.class);
            String role = claims.get("role", String.class);
            req.setAttribute("uid", uid);
            req.setAttribute("role", role);
            req.setAttribute("username", claims.getSubject());

            String path = req.getRequestURI();
            if (path.startsWith("/api/admin/") && !"ADMIN".equals(role)) {
                return deny(resp, 403, "无管理员权限");
            }
            return true;
        } catch (Exception e) {
            return deny(resp, 401, "登录已过期或令牌无效");
        }
    }

    private boolean deny(HttpServletResponse resp, int code, String msg)
            throws Exception {
        resp.setStatus(200);
        resp.setContentType("application/json;charset=UTF-8");
        resp.getWriter().write(mapper.writeValueAsString(Result.fail(code, msg)));
        return false;
    }
}
