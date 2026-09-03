/*
 * UserMapper.java —— 用户表数据访问（注解式 SQL）
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 */
package com.zongshe3.track.mapper;

import com.zongshe3.track.pojo.User;
import org.apache.ibatis.annotations.*;

import java.util.List;

public interface UserMapper {

    @Select("SELECT * FROM t_user WHERE username = #{username}")
    User findByUsername(String username);

    @Select("SELECT * FROM t_user WHERE id = #{id}")
    User findById(Long id);

    @Insert("INSERT INTO t_user(username,password,nickname,role) " +
            "VALUES(#{username},#{password},#{nickname},#{role})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(User user);

    @Update("UPDATE t_user SET password = #{password} WHERE id = #{id}")
    int updatePassword(@Param("id") Long id, @Param("password") String password);

    @Update("UPDATE t_user SET nickname = #{nickname} WHERE id = #{id}")
    int updateNickname(@Param("id") Long id, @Param("nickname") String nickname);

    @Delete("DELETE FROM t_user WHERE id = #{id}")
    int deleteById(Long id);

    /** 管理端分页查询用户（支持关键字模糊匹配用户名/昵称） */
    @Select("<script>" +
            "SELECT * FROM t_user " +
            "<where>" +
            "  <if test='keyword != null and keyword != \"\"'>" +
            "    (username LIKE CONCAT('%',#{keyword},'%') OR nickname LIKE CONCAT('%',#{keyword},'%'))" +
            "  </if>" +
            "</where>" +
            " ORDER BY id DESC LIMIT #{offset},#{size}" +
            "</script>")
    List<User> pageUsers(@Param("keyword") String keyword,
                         @Param("offset") int offset,
                         @Param("size") int size);

    @Select("<script>" +
            "SELECT COUNT(*) FROM t_user " +
            "<where>" +
            "  <if test='keyword != null and keyword != \"\"'>" +
            "    (username LIKE CONCAT('%',#{keyword},'%') OR nickname LIKE CONCAT('%',#{keyword},'%'))" +
            "  </if>" +
            "</where>" +
            "</script>")
    long countUsers(@Param("keyword") String keyword);
}
