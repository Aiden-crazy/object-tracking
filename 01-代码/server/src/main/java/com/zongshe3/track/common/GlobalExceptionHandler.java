/*
 * GlobalExceptionHandler.java —— 全局异常处理
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：将业务异常/参数异常/系统异常统一转换为 Result 返回。
 */
package com.zongshe3.track.common;

import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BizException.class)
    public Result<Void> biz(BizException e) {
        return Result.fail(e.getCode(), e.getMessage());
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public Result<Void> illegal(IllegalArgumentException e) {
        return Result.fail(400, e.getMessage());
    }

    @ExceptionHandler(Exception.class)
    public Result<Void> other(Exception e) {
        log.error("系统异常", e);
        return Result.fail(500, "系统异常: " + e.getMessage());
    }
}
