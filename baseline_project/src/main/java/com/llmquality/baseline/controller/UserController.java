package com.llmquality.baseline.controller;

import com.llmquality.baseline.dto.LoginRequest;
import com.llmquality.baseline.dto.LoginResponse;
import com.llmquality.baseline.dto.UserRequest;
import com.llmquality.baseline.dto.UserResponse;
import com.llmquality.baseline.dto.validation.UserValidationGroups;
import com.llmquality.baseline.exception.ResourceAlreadyExistsException;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.service.interfaces.UserService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;


@RestController
@RequestMapping("${api.base-path}/users")
public class UserController {

    private final UserService userService;


    @Autowired
    public UserController(final UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    public List<UserResponse> listAll() {
        return userService.listAll();
    }

    @GetMapping("/{id}")
    public UserResponse getById(@PathVariable Long id) throws ResourceNotFoundException {
        return userService.getById(id);
    }

    @PostMapping
    public UserResponse create(@RequestBody @Validated(UserValidationGroups.Create.class) UserRequest user)
            throws ResourceAlreadyExistsException {
        return userService.save(user);
    }

    @PutMapping("/{id}")
    public UserResponse update(@PathVariable Long id, @RequestBody @Validated(UserValidationGroups.Update.class) UserRequest user)
            throws ResourceNotFoundException {
        return userService.update(id, user);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) throws ResourceNotFoundException {
        userService.delete(id);
    }

    @PostMapping("/login")
    public LoginResponse login(@RequestBody @Valid LoginRequest loginRequest) throws ResourceNotFoundException {
        return userService.checkLogin(loginRequest);
    }
}
