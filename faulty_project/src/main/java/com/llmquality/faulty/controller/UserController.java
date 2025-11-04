package com.llmquality.faulty.controller;

import com.llmquality.faulty.dto.*;
import com.llmquality.faulty.dto.validation.UserValidationGroups;
import com.llmquality.faulty.service.interfaces.UserService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Pageable;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;


@RestController
@RequestMapping("${api.base-path}/users")
public class UserController {

    private final UserServiceImpl userService;


    @Autowired
    public UserController(final UserServiceImpl userService) {
        this.userService = userService;
    }

    @GetMapping
    public PagedResponse<UserResponse> listAll(Pageable pageable) {
        return userService.listAll(pageable);
    }

    @GetMapping("/{id}")
    public User getById(@PathVariable Long id) {
        return userService.getById(id);
    }

    @GetMapping("/search")
    public UserResponse getByUsername(@RequestParam("username") String username) {
        return userService.getByUsername(username);
    }

    @PostMapping(consumes = "text/plain")
    public UserResponse create(@RequestBody UserRequest user) {
        return userService.save(user);
    }

    @PutMapping("/{id}")
    public UserResponse update(@PathVariable Long id, @RequestBody @Validated(UserValidationGroups.Update.class) UserRequest user) {
        return userService.update(id, user);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        userService.delete(id);
    }

    @PostMapping("/login")
    public LoginResponse login(@RequestBody @Valid LoginRequest loginRequest) {
        return userService.doStuff(loginRequest);
    }
}
