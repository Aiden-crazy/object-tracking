/*
 * TaskService.java —— 任务管理业务逻辑
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：
 *   1) 接收小程序上传的视频/图片，落盘到 storage/origin 并登记任务(PENDING)；
 *   2) 线程池异步执行：状态置 PROCESSING → 调用视觉服务跟踪 →
 *      结果文件复制到 storage/results → 状态置 SUCCESS；失败置 FAILED；
 *   3) 提供任务查询、用户任务列表、管理端全量列表/统计。
 */
package com.zongshe3.track.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.zongshe3.track.common.BizException;
import com.zongshe3.track.mapper.TaskMapper;
import com.zongshe3.track.mapper.UserMapper;
import com.zongshe3.track.pojo.TrackTask;
import com.zongshe3.track.pojo.User;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import jakarta.annotation.PostConstruct;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Slf4j
@Service
@RequiredArgsConstructor
public class TaskService {

    private final TaskMapper taskMapper;
    private final UserMapper userMapper;
    private final VisionClient visionClient;
    private final ObjectMapper mapper = new ObjectMapper();

    /** 文件存储根目录（相对于启动目录） */
    @Value("${app.storage-dir:./uploads}")
    private String storageDir;

    private ExecutorService executor;

    @PostConstruct
    public void init() {
        // 单线程异步处理队列，避免多任务同时压垮视觉服务
        executor = Executors.newSingleThreadExecutor();
        File dir = new File(storageDir);
        if (!dir.exists() && !dir.mkdirs()) {
            log.warn("存储目录创建失败: {}", dir.getAbsolutePath());
        }
    }

    private String webUrlOf(Path p) {
        Path root = Paths.get(storageDir).toAbsolutePath().normalize();
        return "/files/" + root.relativize(p.toAbsolutePath().normalize())
                .toString().replace('\\', '/');
    }

    /** 上传并异步处理（上传立即返回任务ID，前端轮询状态） */
    public TrackTask upload(Long userId, MultipartFile file, String bbox) {
        if (file == null || file.isEmpty()) {
            throw new BizException("上传文件不能为空");
        }
        String mediaType = (file.getContentType() != null
                && file.getContentType().startsWith("image")) ? "IMAGE" : "VIDEO";

        String ext = "";
        String name = file.getOriginalFilename();
        if (name != null && name.contains(".")) {
            ext = name.substring(name.lastIndexOf('.'));
        }
        if (!ext.matches("\\.(mp4|avi|mov|mkv|jpg|jpeg|png|bmp|webp)")) {
            throw new BizException("仅支持 mp4/avi/mov/mkv 视频与 jpg/png 等图片格式");
        }
        if (bbox != null && !bbox.isBlank()) {
            String[] parts = bbox.trim().split(",");
            if (parts.length != 4) {
                throw new BizException("bbox 格式应为 x,y,w,h");
            }
            for (String p : parts) {
                if (!p.matches("\\d+")) {
                    throw new BizException("bbox 必须为数字");
                }
            }
        }

        TrackTask task = new TrackTask();
        task.setUserId(userId);
        task.setMediaType(mediaType);
        task.setFileName(name);
        task.setBbox(bbox);
        try {
            Path origin = Paths.get(storageDir, "origin");
            Files.createDirectories(origin);
            Path saved = origin.resolve(UUID.randomUUID().toString().substring(0, 8) + ext);
            Files.copy(file.getInputStream(), saved, StandardCopyOption.REPLACE_EXISTING);
            task.setFilePath(saved.toAbsolutePath().toString());
            taskMapper.insert(task);
        } catch (IOException e) {
            log.error("保存上传文件失败", e);
            throw new BizException("文件保存失败: " + e.getMessage());
        }

        final Long taskId = task.getId();
        executor.submit(() -> process(taskId));
        return task;
    }

    /** 异步执行：PENDING -> PROCESSING -> SUCCESS/FAILED */
    private void process(Long taskId) {
        TrackTask task = taskMapper.findById(taskId);
        if (task == null) {
            return;
        }
        taskMapper.markProcessing(taskId);
        try {
            Map<String, String> r = visionClient.track(task.getFilePath(), task.getBbox());
            // 将结果视频与日志复制进本服务存储目录，便于 /files/** 访问
            Path results = Paths.get(storageDir, "results");
            Files.createDirectories(results);
            Path vidSrc = Paths.get(r.get("resultVideo"));
            Path logSrc = Paths.get(r.get("logFile"));
            Path vidDst = results.resolve(taskId + "_tracked.mp4");
            Path logDst = results.resolve(taskId + "_log.json");
            if (Files.exists(vidSrc)) {
                Files.copy(vidSrc, vidDst, StandardCopyOption.REPLACE_EXISTING);
            }
            if (Files.exists(logSrc)) {
                Files.copy(logSrc, logDst, StandardCopyOption.REPLACE_EXISTING);
            }
            taskMapper.markSuccess(taskId,
                    Files.exists(vidDst) ? webUrlOf(vidDst) : null,
                    Files.exists(logDst) ? webUrlOf(logDst) : null,
                    r.get("statsJson"));
            log.info("任务 {} 处理成功", taskId);
        } catch (Exception e) {
            log.error("任务 {} 处理失败", taskId, e);
            taskMapper.markFailed(taskId,
                    e.getMessage() == null ? "未知错误" : e.getMessage().substring(0,
                            Math.min(e.getMessage().length(), 400)));
        }
    }

    // ---------------- 查询 ----------------

    public TrackTask getTask(Long taskId) {
        TrackTask t = taskMapper.findById(taskId);
        if (t == null) {
            throw new BizException("任务不存在");
        }
        return t;
    }

    /** 我的任务列表（分页） */
    public Map<String, Object> myTasks(Long userId, int page, int size) {
        page = Math.max(page, 1);
        size = Math.min(Math.max(size, 1), 100);
        List<TrackTask> list = taskMapper.pageByUser(userId, (page - 1) * size, size);
        Map<String, Object> data = new HashMap<>();
        data.put("total", taskMapper.countByUser(userId));
        data.put("list", list);
        return data;
    }

    /** 管理端任务列表（分页 + 状态过滤） */
    public Map<String, Object> adminTasks(String status, int page, int size) {
        page = Math.max(page, 1);
        size = Math.min(Math.max(size, 1), 100);
        List<TrackTask> list = taskMapper.pageAll(status, (page - 1) * size, size);
        Map<String, Object> data = new HashMap<>();
        data.put("total", taskMapper.countAll(status));
        data.put("list", list);
        return data;
    }

    public void deleteTask(Long taskId) {
        if (taskMapper.findById(taskId) == null) {
            throw new BizException("任务不存在");
        }
        taskMapper.deleteById(taskId);
    }

    /** 管理端统计卡片：用户总数 / 任务总数 / 各状态数 */
    public Map<String, Object> stats() {
        Map<String, Object> data = new HashMap<>();
        data.put("userCount", userMapper.countUsers(null));
        data.put("taskCount", taskMapper.taskTotal());
        data.put("successCount", taskMapper.taskSuccess());
        data.put("processingCount", taskMapper.taskProcessing());
        data.put("failedCount", taskMapper.taskFailed());
        return data;
    }
}
