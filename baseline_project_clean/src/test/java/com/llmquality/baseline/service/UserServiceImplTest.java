package com.llmquality.baseline.service;

import com.llmquality.baseline.dto.*;
import com.llmquality.baseline.entity.User;
import com.llmquality.baseline.exception.ResourceAlreadyExistsException;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.exception.UnauthorizedException;
import com.llmquality.baseline.mapper.UserMapper;
import com.llmquality.baseline.repository.UserRepository;
import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserServiceImplTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    @Mock
    private UserMapper userMapper;

    @Mock
    private EntityManager entityManager;

    @Mock
    private JwtEncoder jwtEncoder;

    @InjectMocks
    private UserServiceImpl userService;


    @Test
    void delete_userExists_deletesUser() {
        Long id = 1L;
        User user = createMockUser(id);
        when(userRepository.findById(id)).thenReturn(Optional.of(user));

        userService.delete(id);

        verify(userRepository).delete(user); // Exposes bug: prod calls delete but logs before, verify passes but check impl
    }


    private User createMockUser(Long id) {
        User user = new User();
        user.setId(id);
        user.setUsername("user" + id);
        user.setEmail("user" + id + "@example.com");
        user.setAdmin(false);
        user.setPassword("hashed");
        return user;
    }
}