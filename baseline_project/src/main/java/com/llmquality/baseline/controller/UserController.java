package com.llmquality.baseline.controller;

import com.llmquality.baseline.dto.*;
import com.llmquality.baseline.service.interfaces.UserService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.web.PageableDefault;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import static com.llmquality.baseline.dto.validation.UserValidationGroups.*;


@RestController
@RequestMapping("${api.base-path}/users")
public class UserController {

    private final UserService userService;

    @Autowired
    public UserController(UserService userService) {
        this.userService = userService;
    }


    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public PagedResponse<UserResponse> listAll(@PageableDefault(sort = "id", direction = Sort.Direction.ASC) Pageable pageable) {
        return userService.listAll(pageable);
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN') or @sec.isOwner(#id, authentication)")
    public UserResponse getById(@PathVariable Long id) {
        return userService.getById(id);
    }

    @GetMapping("/search")
    @PreAuthorize("hasRole('ADMIN')")
    public UserResponse getByUsername(@RequestParam("username") String username) {
        return userService.getByUsername(username);
    }

    @PostMapping
    @PreAuthorize("hasRole('ADMIN') or @sec.canSetAdminFlag(#userRequest.admin, authentication)")
    public UserResponse create(@RequestBody UserRequest userRequest) {
        return userService.save(userRequest);
    }

    @PatchMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN') or (@sec.isOwner(#id, authentication) and @sec.canSetAdminFlag(#userRequest.admin, authentication))")
    public UserResponse update(@PathVariable Long id, @RequestBody @Validated(Update.class) UserRequest userRequest) {
        return userService.update(id, userRequest);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        userService.delete(id);
    }

    @PostMapping("/login")
    public LoginResponse login(@RequestBody @Valid LoginRequest loginRequest) {
        return userService.checkLogin(loginRequest);
    }
}
