package com.llmquality.baseline.controller;

import com.llmquality.baseline.dto.user.*;
import com.llmquality.baseline.service.interfaces.UserService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Pageable;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import static com.llmquality.baseline.dto.user.validation.UserValidationGroups.*;


@RestController
@RequestMapping("${api.base-path}/users")
@Validated
public class UserController {

    private final UserService userService;


    @Autowired
    public UserController(final UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    @PreAuthorize("hasRole('ROLE_ADMIN')")
    public PagedResponse<UserResponse> listAll(Pageable pageable) {
        return userService.listAll(pageable);
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasRole('ROLE_ADMIN') or #id == authentication.principal.id")
    public UserResponse getById(@PathVariable Long id) {
        return userService.getById(id);
    }

    @GetMapping("/search")
    @PreAuthorize("hasRole('ROLE_ADMIN')")
    public UserResponse getByUsername(@RequestParam("username") String username) {
        return userService.getByUsername(username);
    }

    @PostMapping
    public UserResponse create(@RequestBody @Validated(Create.class) UserRequest user) {
        return userService.save(user);
    }

    @PatchMapping("/{id}")
    @PreAuthorize("hasRole('ROLE_ADMIN') or #id == authentication.principal.id")
    public UserResponse update(@PathVariable Long id, @RequestBody @Validated(Update.class) UserRequest user) {
        return userService.update(id, user);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ROLE_ADMIN')")
    public void delete(@PathVariable Long id) {
        userService.delete(id);
    }

    @PostMapping("/login")
    public LoginResponse login(@RequestBody @Valid LoginRequest loginRequest) {
        return userService.checkLogin(loginRequest);
    }
}
