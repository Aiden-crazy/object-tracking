/*
 * VisionClient.java —— 视觉处理服务客户端
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：使用 JDK HttpClient 调用 Python 视觉服务
 *           POST {vision-url}/api/v1/track_local，传递本地视频路径与 bbox，
 *           解析返回的结果视频/日志路径。
 */
package com.zongshe3.track.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zongshe3.track.common.BizException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
public class VisionClient {

    private final HttpClient client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10)).build();
    private final ObjectMapper mapper = new ObjectMapper();

    @Value("${app.vision-url:http://127.0.0.1:9000}")
    private String visionUrl;

    /**
     * 首帧准备：让视觉服务提取首帧图片，并给出自动识别的目标框建议。
     * 供小程序"先看首帧图、再手指画框"的两段式流程使用。
     *
     * @param videoPath 服务器本地视频绝对路径
     * @param outImage  首帧图片的输出绝对路径（由本服务指定，便于直接落到 /files 可访问目录）
     * @return {image: 图片绝对路径, width, height, autoBbox: "x,y,w,h" 或空串}
     */
    public Map<String, String> prepare(String videoPath, String outImage) {
        try {
            Map<String, String> body = new HashMap<>();
            body.put("video_path", videoPath);
            body.put("out_image", outImage);
            String json = mapper.writeValueAsString(body);
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(visionUrl + "/api/v1/prepare"))
                    .timeout(Duration.ofSeconds(120))
                    .header("Content-Type", "application/json; charset=utf-8")
                    .POST(HttpRequest.BodyPublishers.ofString(json))
                    .build();
            HttpResponse<String> resp = client.send(req,
                    HttpResponse.BodyHandlers.ofString());
            JsonNode node = mapper.readTree(resp.body());
            if (node.path("code").asInt() != 0) {
                throw new BizException("视觉服务返回错误: " + node.path("msg").asText());
            }
            Map<String, String> out = new HashMap<>();
            out.put("image", node.path("image").asText());
            out.put("width", String.valueOf(node.path("width").asInt()));
            out.put("height", String.valueOf(node.path("height").asInt()));
            out.put("autoBbox", node.path("auto_bbox").isNull()
                    ? "" : node.path("auto_bbox").asText());
            return out;
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            log.error("调用视觉服务(prepare)失败", e);
            throw new BizException("首帧提取失败，请确认 python api_service.py 已启动: "
                    + e.getMessage());
        }
    }

    /**
     * 调用视觉服务进行单目标跟踪。
     *
     * @param videoPath 服务器本地视频/图片绝对路径
     * @param bbox      目标框 "x,y,w,h"，可空（视频=自动识别运动目标，图片=画面中央区域）
     * @return {resultVideo: 结果文件绝对路径(视频.mp4/图片.jpg), logFile: 日志绝对路径,
     *          statsJson: 统计JSON文本, mediaType: VIDEO/IMAGE}
     */
    public Map<String, String> track(String videoPath, String bbox) {
        try {
            Map<String, String> body = new HashMap<>();
            body.put("video_path", videoPath);
            if (bbox != null && !bbox.isBlank()) {
                body.put("bbox", bbox);
            }
            String json = mapper.writeValueAsString(body);
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(visionUrl + "/api/v1/track_local"))
                    .timeout(Duration.ofSeconds(300))
                    .header("Content-Type", "application/json; charset=utf-8")
                    .POST(HttpRequest.BodyPublishers.ofString(json))
                    .build();
            HttpResponse<String> resp = client.send(req,
                    HttpResponse.BodyHandlers.ofString());
            JsonNode node = mapper.readTree(resp.body());
            if (node.path("code").asInt() != 0) {
                throw new BizException("视觉服务返回错误: " + node.path("msg").asText());
            }
            Map<String, String> out = new HashMap<>();
            out.put("resultVideo", node.path("result_video").asText());
            out.put("logFile", node.path("log_file").asText());
            out.put("statsJson", node.path("stats").toString());
            out.put("mediaType", node.path("media_type").asText("VIDEO"));
            return out;
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            log.error("调用视觉服务失败", e);
            throw new BizException("视觉服务调用失败，请确认 python api_service.py 已启动: "
                    + e.getMessage());
        }
    }
}
