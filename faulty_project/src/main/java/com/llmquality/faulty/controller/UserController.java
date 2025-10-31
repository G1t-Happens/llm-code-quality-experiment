package com.llmquality.faulty.controller;

import com.llmquality.faulty.dto.LoginRequest;
import com.llmquality.faulty.dto.UserRequest;
import com.llmquality.faulty.dto.UserResponse;
import com.llmquality.faulty.dto.validation.UserValidationGroups;
import com.llmquality.faulty.exception.ResourceAlreadyExistsException;
import com.llmquality.faulty.exception.ResourceNotFoundException;
import com.llmquality.faulty.service.interfaces.UserService;
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
    public boolean login(@RequestBody @Valid LoginRequest loginRequest) {
        return userService.checkLogin(loginRequest);
    }
}
