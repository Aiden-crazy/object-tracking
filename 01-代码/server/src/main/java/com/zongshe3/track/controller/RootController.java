/*
 * RootController.java —— 根路径跳转
 * 作者：【姓名】  学号：【学号】  创建时间：2026-07
 * 功能描述：根路径 "/" 优先由 static/index.html（系统首页）承接；
 *           访问 /index 时也跳转到首页，避免出现 Whitelabel 404 错误页。
 */
package com.zongshe3.track.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class RootController {

    @GetMapping({"/", "/index"})
    public String root() {
        return "redirect:/index.html";
    }
}
