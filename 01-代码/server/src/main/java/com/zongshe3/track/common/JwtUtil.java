/*
 * JwtUtil.java —— JWT 令牌工具
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：登录成功后签发 HS256 JWT，拦截器校验并解析 uid/role。
 */
package com.zongshe3.track.common;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

public class JwtUtil {

    /** HS256 要求密钥长度 >= 32 字节 */
    private static final SecretKey KEY = Keys.hmacShaKeyFor(
            "ZongShe3-Track-Server-Secret-Key-2026-07-CourseDesign-Token"
                    .getBytes(StandardCharsets.UTF_8));

    /** 有效期 7 天 */
    private static final long EXPIRE_MS = 7L * 24 * 3600 * 1000;

    public static String createToken(Long uid, String username, String role) {
        return Jwts.builder()
                .setSubject(username)
                .claim("uid", uid)
                .claim("role", role)
                .setIssuedAt(new Date())
                .setExpiration(new Date(System.currentTimeMillis() + EXPIRE_MS))
                .signWith(KEY, SignatureAlgorithm.HS256)
                .compact();
    }

    public static Claims parse(String token) {
        return Jwts.parserBuilder().setSigningKey(KEY).build()
                .parseClaimsJws(token).getBody();
    }
}
