-- ============================================================
-- init.sql —— 综合实践III《单目标跟踪系统》数据库初始化脚本
-- 作者：【姓名】  学号：【学号】  创建时间：2026-07
-- 功能描述：创建数据库 zongshe3_track 及用户表、任务表。
-- 执行方式：mysql -uroot -p123456 < init.sql
-- ============================================================
CREATE DATABASE IF NOT EXISTS zongshe3_track
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE zongshe3_track;

-- 用户表：普通用户 + 管理员
DROP TABLE IF EXISTS t_user;
CREATE TABLE t_user (
  id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  username    VARCHAR(50)  NOT NULL COMMENT '用户名(唯一)',
  password    VARCHAR(100) NOT NULL COMMENT '密码(BCrypt加密)',
  nickname    VARCHAR(50)  DEFAULT NULL COMMENT '昵称',
  role        VARCHAR(10)  NOT NULL DEFAULT 'USER' COMMENT '角色 USER/ADMIN',
  create_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_username (username)
) ENGINE = InnoDB COMMENT ='用户表';

-- 任务表：小程序提交的视频/图片与视觉处理结果
DROP TABLE IF EXISTS t_task;
CREATE TABLE t_task (
  id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id     BIGINT       NOT NULL COMMENT '提交用户ID',
  media_type  VARCHAR(10)  NOT NULL DEFAULT 'VIDEO' COMMENT '媒体类型 VIDEO/IMAGE',
  file_name   VARCHAR(255) DEFAULT NULL COMMENT '原始文件名',
  file_path   VARCHAR(500) DEFAULT NULL COMMENT '原始文件存储路径',
  bbox        VARCHAR(50)  DEFAULT NULL COMMENT '首帧目标框 x,y,w,h(可空=自动居中)',
  status      VARCHAR(20)  NOT NULL DEFAULT 'PENDING'
              COMMENT 'PENDING/PROCESSING/SUCCESS/FAILED',
  result_path VARCHAR(500) DEFAULT NULL COMMENT '结果视频访问路径',
  log_path    VARCHAR(500) DEFAULT NULL COMMENT '跟踪日志访问路径',
  stats_json  TEXT         DEFAULT NULL COMMENT '跟踪统计信息(JSON)',
  error_msg   VARCHAR(500) DEFAULT NULL COMMENT '失败原因',
  create_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  finish_time DATETIME     DEFAULT NULL COMMENT '完成时间',
  PRIMARY KEY (id),
  KEY idx_user (user_id),
  KEY idx_status (status)
) ENGINE = InnoDB COMMENT ='视觉处理任务表';

-- 默认管理员账号（密码 123456，启动时若不存在则由程序自动补齐，见 AdminInitializer）
