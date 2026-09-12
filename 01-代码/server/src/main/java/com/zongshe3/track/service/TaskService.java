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
import java.util.Objects;
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

    /** 校验并规范化 bbox；空白返回 null（null 表示交给视觉服务自动识别目标） */
    private String normalizeBbox(String bbox) {
        if (bbox == null || bbox.isBlank()) {
            return null;
        }
        String[] parts = bbox.trim().split(",");
        if (parts.length != 4) {
            throw new BizException("bbox 格式应为 x,y,w,h");
        }
        StringBuilder sb = new StringBuilder();
        for (String p : parts) {
            String v = p.trim();
            if (!v.matches("\\d+")) {
                throw new BizException("bbox 必须为数字");
            }
            if (sb.length() > 0) {
                sb.append(',');
            }
            sb.append(v);
        }
        return sb.toString();
    }

    /** 上传并异步处理（上传立即返回任务ID，前端轮询状态） */
    public TrackTask upload(Long userId, MultipartFile file, String bbox) {
        return upload(userId, file, bbox, false);
    }

    /** 图片扩展名（用于判定素材类型；不能只信 Content-Type，小程序上传常为 octet-stream） */
    private static final java.util.Set<String> IMAGE_EXTS = java.util.Set.of(
            ".jpg", ".jpeg", ".png", ".bmp", ".webp");

    /**
     * 上传。
     * defer=false：老流程，上传即异步跟踪（Web 端、老版小程序用）。
     * defer=true ：两段式第一步，只落盘建任务(PENDING)、提取首帧图与自动目标框，
     *              先返回给客户端画框，等用户框完再调 start() 开始跟踪。
     */
    public TrackTask upload(Long userId, MultipartFile file, String bbox, boolean defer) {
        if (file == null || file.isEmpty()) {
            throw new BizException("上传文件不能为空");
        }

        String ext = "";
        String name = file.getOriginalFilename();
        if (name != null && name.contains(".")) {
            ext = name.substring(name.lastIndexOf('.')).toLowerCase();
        }
        if (!ext.matches("\\.(mp4|avi|mov|mkv|jpg|jpeg|png|bmp|webp)")) {
            throw new BizException("仅支持 mp4/avi/mov/mkv 视频与 jpg/png 等图片格式");
        }
        // 素材类型：扩展名优先，其次看 Content-Type
        String mediaType = IMAGE_EXTS.contains(ext)
                || (file.getContentType() != null
                    && file.getContentType().startsWith("image"))
                ? "IMAGE" : "VIDEO";
        String normBbox = normalizeBbox(bbox);

        TrackTask task = new TrackTask();
        task.setUserId(userId);
        task.setMediaType(mediaType);
        task.setFileName(name);
        task.setBbox(normBbox);
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

        // 状态由 SQL 里的 'PENDING' 写入，这里同步回填到对象，
        // 否则接口返回的 JSON 里 status 会是 null（旧版一直如此）
        task.setStatus("PENDING");

        final Long taskId = task.getId();
        if (defer) {
            prepareFrame(task);
        } else {
            executor.submit(() -> process(taskId));
        }
        return task;
    }

    /**
     * 两段式第一步的内部实现：调用视觉服务提取首帧并自动识别目标框。
     * 首帧图片直接由视觉服务写到本服务的 uploads/frames/ 下，便于 /files/** 访问。
     * 失败时删除刚建的任务，避免留下只能干等的 PENDING 记录。
     */
    private void prepareFrame(TrackTask task) {
        try {
            Path frames = Paths.get(storageDir, "frames");
            Files.createDirectories(frames);
            Path dst = frames.resolve(task.getId() + ".jpg").toAbsolutePath();
            Map<String, String> r = visionClient.prepare(
                    task.getFilePath(), dst.toString());
            task.setFrameUrl(webUrlOf(dst));
            task.setImgWidth(parseIntSafe(r.get("width")));
            task.setImgHeight(parseIntSafe(r.get("height")));
            String ab = r.get("autoBbox");
            task.setAutoBbox(ab == null || ab.isBlank() ? null : ab);
            log.info("任务 {} 首帧就绪: {} ({}x{}), 自动框={}",
                    task.getId(), task.getFrameUrl(), task.getImgWidth(),
                    task.getImgHeight(), task.getAutoBbox());
        } catch (Exception e) {
            log.error("任务 {} 提取首帧失败", task.getId(), e);
            try {
                taskMapper.deleteById(task.getId());
            } catch (Exception ignore) {
                // 清理失败不影响主流程报错
            }
            throw new BizException(e.getMessage() == null ? "首帧提取失败" : e.getMessage());
        }
    }

    private Integer parseIntSafe(String s) {
        try {
            return Integer.valueOf(s);
        } catch (Exception e) {
            return null;
        }
    }

    /** 两段式第二步：带上用户手指框选的目标框开始处理（bbox 为空则用自动识别结果） */
    public TrackTask start(Long taskId, String bbox, Long userId, String role) {
        TrackTask task = getTask(taskId, userId, role);   // 含归属校验
        if (!"PENDING".equals(task.getStatus())) {
            throw new BizException("该任务已开始处理或已结束");
        }
        String norm = normalizeBbox(bbox);
        taskMapper.updateBbox(taskId, norm);
        task.setBbox(norm);
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
            // 将结果与日志复制进本服务存储目录，便于 /files/** 访问
            // 视频输出 *.mp4，图片输出 *.jpg（视觉服务按素材类型决定）
            boolean isImage = "IMAGE".equals(task.getMediaType());
            String resultName = taskId + (isImage ? "_tracked.jpg" : "_tracked.mp4");
            Path results = Paths.get(storageDir, "results");
            Files.createDirectories(results);
            Path vidSrc = Paths.get(r.get("resultVideo"));
            Path logSrc = Paths.get(r.get("logFile"));
            Path vidDst = results.resolve(resultName);
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

    /**
     * 查询任务详情。**必须做归属校验**：普通用户只能看自己的任务，
     * 否则只要猜到自增 id 就能拿到别人的文件路径与结果（越权访问）。
     */
    public TrackTask getTask(Long taskId, Long userId, String role) {
        TrackTask t = taskMapper.findById(taskId);
        if (t == null) {
            throw new BizException("任务不存在");
        }
        if (!"ADMIN".equals(role) && !Objects.equals(t.getUserId(), userId)) {
            throw new BizException(403, "无权访问该任务");
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
