package com.llmquality.baseline.controller;

import com.llmquality.baseline.dto.*;
import com.llmquality.baseline.service.interfaces.UserService;
import jakarta.validation.Valid;
import org.springframework.data.domain.Pageable;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import static com.llmquality.baseline.dto.validation.UserValidationGroups.*;


@RestController
@RequestMapping("${api.base-path}/users")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }


    @GetMapping
    @PreAuthorize("@sec.isAdmin(authentication)")
    public PagedResponse<UserResponse> listAll(Pageable pageable) {
        return userService.listAll(pageable);
    }

    @GetMapping("/{id}")
    @PreAuthorize("@sec.isAdmin(authentication) or @sec.isOwner(#id, authentication)")
    public UserResponse getById(@PathVariable Long id) {
        return userService.getById(id);
    }

    @GetMapping("/search")
    @PreAuthorize("@sec.isAdmin(authentication)")
    public UserResponse getByUsername(@RequestParam("username") String username) {
        return userService.getByUsername(username);
    }

    @PostMapping
    @PreAuthorize("@sec.isAdmin(authentication) or @sec.canSetAdminFlag(#userRequest.admin, authentication)")
    public UserResponse create(@RequestBody @Validated(Create.class) UserRequest userRequest) {
        return userService.save(userRequest);
    }

    @PatchMapping("/{id}")
    @PreAuthorize("@sec.isAdmin(authentication) or (@sec.isOwner(#id, authentication) && @sec.canSetAdminFlag(#userRequest.admin, authentication))")
    public UserResponse update(@PathVariable Long id, @RequestBody @Validated(Update.class) UserRequest userRequest) {
        return userService.update(id, userRequest);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("@sec.isAdmin(authentication)")
    public void delete(@PathVariable Long id) {
        userService.delete(id);
    }

    @PostMapping("/login")
    public LoginResponse login(@RequestBody @Valid LoginRequest loginRequest) {
        return userService.checkLogin(loginRequest);
    }
}
