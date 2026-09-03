/*
 * User.java —— 用户实体（对应表 t_user）
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 */
package com.zongshe3.track.pojo;

import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;

import java.time.LocalDateTime;

@Data
public class User {
    private Long id;
    private String username;
    /** 密码不参与 JSON 序列化返回前端 */
    @JsonIgnore
    private String password;
    private String nickname;
    /** USER 或 ADMIN */
    private String role;
    private LocalDateTime createTime;
}
