package com.llmquality.baseline.controller;

import com.llmquality.baseline.dto.*;
import com.llmquality.baseline.dto.validation.UserValidationGroups;
import com.llmquality.baseline.service.interfaces.UserService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Pageable;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;


@RestController
@RequestMapping("${api.base-path}/users")
public class UserController {

    private final UserService userService;


    @Autowired
    public UserController(final UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    public PagedResponse<UserResponse> listAll(Pageable pageable) {
        return userService.listAll(pageable);
    }

    @GetMapping("/{id}")
    public UserResponse getById(@PathVariable Long id) {
        return userService.getById(id);
    }

    @PostMapping
    public UserResponse create(@RequestBody @Validated(UserValidationGroups.Create.class) UserRequest user) {
        return userService.save(user);
    }

    @PatchMapping("/{id}")
    public UserResponse update(@PathVariable Long id, @RequestBody @Validated(UserValidationGroups.Update.class) UserRequest user) {
        return userService.update(id, user);
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
