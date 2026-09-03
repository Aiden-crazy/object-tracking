/*
 * BizException.java —— 业务异常
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 */
package com.zongshe3.track.common;

public class BizException extends RuntimeException {
    private final int code;

    public BizException(String msg) {
        this(400, msg);
    }

    public BizException(int code, String msg) {
        super(msg);
        this.code = code;
    }

    public int getCode() {
        return code;
    }
}
