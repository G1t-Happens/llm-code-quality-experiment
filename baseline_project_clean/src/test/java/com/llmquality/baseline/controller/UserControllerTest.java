package com.llmquality.baseline.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.llmquality.baseline.dto.LoginRequest;
import com.llmquality.baseline.dto.UserRequest;
import com.llmquality.baseline.dto.UserResponse;
import com.llmquality.baseline.service.interfaces.UserService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(UserController.class)
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private UserService userService;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    @WithMockUser(roles = "ADMIN")
    void listAll_adminAccess_returnsPagedUsers() throws Exception {
        mockMvc.perform(get("/api/v1/users?page=0&size=10"))
                .andExpect(status().isOk());
    }

    @Test
    void create_noAuth_failsDueToPreAuthorize() throws Exception {
        UserRequest request = new UserRequest("newuser", "Password1a", "new@example.com", false);

        mockMvc.perform(post("/api/v1/users")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isForbidden()); // Exposes security, but permitAll in config, but PreAuthorize
    }
}