/*
 * TaskMapper.java —— 任务表数据访问（注解式 SQL）
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 */
package com.zongshe3.track.mapper;

import com.zongshe3.track.pojo.TrackTask;
import org.apache.ibatis.annotations.*;

import java.util.List;

public interface TaskMapper {

    @Insert("INSERT INTO t_task(user_id,media_type,file_name,file_path,bbox,status) " +
            "VALUES(#{userId},#{mediaType},#{fileName},#{filePath},#{bbox},'PENDING')")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(TrackTask task);

    @Select("SELECT * FROM t_task WHERE id = #{id}")
    TrackTask findById(Long id);

    @Update("UPDATE t_task SET status='PROCESSING' WHERE id=#{id} AND status='PENDING'")
    int markProcessing(Long id);

    /** 两段式流程：用户画完框后再回填 bbox（仅允许未开始的任务） */
    @Update("UPDATE t_task SET bbox=#{bbox} WHERE id=#{id} AND status='PENDING'")
    int updateBbox(@Param("id") Long id, @Param("bbox") String bbox);

    @Update("UPDATE t_task SET status='SUCCESS', result_path=#{resultPath}, " +
            "log_path=#{logPath}, stats_json=#{statsJson}, finish_time=NOW() " +
            "WHERE id=#{id}")
    int markSuccess(@Param("id") Long id, @Param("resultPath") String resultPath,
                    @Param("logPath") String logPath,
                    @Param("statsJson") String statsJson);

    @Update("UPDATE t_task SET status='FAILED', error_msg=#{errorMsg}, " +
            "finish_time=NOW() WHERE id=#{id}")
    int markFailed(@Param("id") Long id, @Param("errorMsg") String errorMsg);

    /** 某用户的任务列表（分页） */
    @Select("SELECT * FROM t_task WHERE user_id=#{userId} " +
            "ORDER BY id DESC LIMIT #{offset},#{size}")
    List<TrackTask> pageByUser(@Param("userId") Long userId,
                               @Param("offset") int offset,
                               @Param("size") int size);

    @Select("SELECT COUNT(*) FROM t_task WHERE user_id=#{userId}")
    long countByUser(Long userId);

    /** 管理端：全量任务分页（可过滤状态，附带用户名） */
    @Select("<script>" +
            "SELECT t.*, u.username FROM t_task t " +
            "LEFT JOIN t_user u ON t.user_id = u.id " +
            "<where>" +
            "  <if test='status != null and status != \"\"'>t.status = #{status}</if>" +
            "</where>" +
            "ORDER BY t.id DESC LIMIT #{offset},#{size}" +
            "</script>")
    List<TrackTask> pageAll(@Param("status") String status,
                            @Param("offset") int offset,
                            @Param("size") int size);

    @Select("<script>" +
            "SELECT COUNT(*) FROM t_task t " +
            "<where>" +
            "  <if test='status != null and status != \"\"'>t.status = #{status}</if>" +
            "</where>" +
            "</script>")
    long countAll(@Param("status") String status);

    @Delete("DELETE FROM t_task WHERE id=#{id}")
    int deleteById(Long id);

    @Delete("DELETE FROM t_task WHERE user_id=#{userId}")
    int deleteByUserId(Long userId);

    /** 统计卡片 */
    @Select("SELECT COUNT(*) FROM t_task")
    long taskTotal();

    @Select("SELECT COUNT(*) FROM t_task WHERE status='SUCCESS'")
    long taskSuccess();

    @Select("SELECT COUNT(*) FROM t_task WHERE status='PROCESSING'")
    long taskProcessing();

    @Select("SELECT COUNT(*) FROM t_task WHERE status='FAILED'")
    long taskFailed();
}
