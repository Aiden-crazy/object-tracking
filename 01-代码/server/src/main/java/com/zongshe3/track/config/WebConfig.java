/*
 * WebConfig.java —— Web MVC 配置
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：
 *   1) 注册 JWT 拦截器（仅拦 /api/**，放行 /api/auth/** 与静态资源）；
 *   2) /files/** 映射到磁盘存储目录，供 <video>/<img> 直接播放结果；
 *   3) 全局 CORS（便于小程序开发调试与跨域调用）。
 */
package com.zongshe3.track.config;

import com.zongshe3.track.interceptor.AuthInterceptor;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.io.File;

@Configuration
@RequiredArgsConstructor
public class WebConfig implements WebMvcConfigurer {

    private final AuthInterceptor authInterceptor;

    @Value("${app.storage-dir:./uploads}")
    private String storageDir;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(authInterceptor)
                .addPathPatterns("/api/**")
                .excludePathPatterns("/api/auth/**", "/error");
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        String abs = new File(storageDir).getAbsolutePath();
        registry.addResourceHandler("/files/**")
                .addResourceLocations("file:" + abs + File.separator);
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("*")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }
}
