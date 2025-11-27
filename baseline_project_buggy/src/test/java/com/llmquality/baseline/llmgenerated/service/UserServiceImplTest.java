package com.llmquality.baseline.llmgenerated.service;

import com.llmquality.baseline.dto.*;
import com.llmquality.baseline.entity.User;
import com.llmquality.baseline.exception.ResourceAlreadyExistsException;
import com.llmquality.baseline.exception.ResourceNotFoundException;
import com.llmquality.baseline.exception.UnauthorizedException;
import com.llmquality.baseline.mapper.UserMapper;
import com.llmquality.baseline.repository.UserRepository;
import com.llmquality.baseline.service.UserServiceImpl;
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
    void listAll_returnsPagedResponseRespectingPageable() {
        Pageable pageable = PageRequest.of(1, 5);
        List<User> allUsers = List.of(createMockUser(1L), createMockUser(2L), createMockUser(3L), createMockUser(4L),
                createMockUser(5L), createMockUser(6L), createMockUser(7L), createMockUser(8L), createMockUser(9L), createMockUser(10L),
                createMockUser(11L));
        when(userRepository.findAll()).thenReturn(allUsers);
        UserResponse mockResponse = new UserResponse(1L, "user1", "user1@example.com", false);
        when(userMapper.toUserResponse(any(User.class))).thenReturn(mockResponse);

        PagedResponse<UserResponse> result = userService.listAll(pageable);

        assertNotNull(result);
        assertEquals(11, result.totalElements()); // total correct
        assertEquals(5, result.content().size()); // Fails
        verify(userRepository).findAll(); // No pageable used, exposes bug
    }

    @Test
    void getById_userExists_returnsUserResponse() {
        Long id = 1L;
        User user = createMockUser(id);
        UserResponse expected = new UserResponse(id, "user1", "user1@example.com", false);
        when(userRepository.findById(id)).thenReturn(Optional.of(user));
        when(userMapper.toUserResponse(user)).thenReturn(expected);

        UserResponse result = userService.getById(id);

        assertEquals(expected, result);
    }

    @Test
    void getById_userNotFound_throwsResourceNotFoundException() {
        Long id = 999L;
        when(userRepository.findById(id)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> userService.getById(id));
    }

    @Test
    void save_userNew_persistsAndReturnsUserResponse() {
        UserRequest request = new UserRequest("newuser", "Password1a", "new@example.com", true);
        User newUser = createMockUser(null);
        newUser.setUsername("newuser");
        UserResponse expected = new UserResponse(1L, "newuser", "new@example.com", true);
        when(userRepository.existsByUsername("newuser")).thenReturn(false);
        when(userMapper.toUserEntity(request, passwordEncoder)).thenReturn(newUser);
        when(userRepository.save(newUser)).thenReturn(newUser);
        when(userMapper.toUserResponse(newUser)).thenReturn(expected);

        UserResponse result = userService.save(request);

        assertEquals(expected, result);
        verify(userRepository).save(newUser);
    }

    @Test
    void save_usernameExists_throwsResourceAlreadyExistsException() {
        UserRequest request = new UserRequest("existing", "Password1a", "test@example.com", false);
        when(userRepository.existsByUsername("existing")).thenReturn(true);

        assertThrows(ResourceAlreadyExistsException.class, () -> userService.save(request));
    }

    @Test
    void update_userExists_updatesAndReturnsUserResponse() {
        Long id = 1L;
        UserRequest request = new UserRequest("updated", "NewPass1a", "updated@example.com", true);
        User existingUser = createMockUser(id);
        User savedUser = createMockUser(id);
        UserResponse expected = new UserResponse(id, "updated", "updated@example.com", true);
        when(userRepository.findById(id)).thenReturn(Optional.of(existingUser));
        when(userRepository.existsByUsername("updated")).thenReturn(false);
        when(userMapper.updateUserEntityFromUserRequest(request, existingUser, passwordEncoder)).thenReturn(savedUser);
        when(userRepository.save(savedUser)).thenReturn(savedUser);
        when(userMapper.toUserResponse(savedUser)).thenReturn(expected);

        UserResponse result = userService.update(id, request);

        assertEquals(expected, result);
        verify(userRepository).save(savedUser);
    }

    @Test
    void update_userNotFound_throwsResourceNotFoundException() {
        Long id = 999L;
        UserRequest request = new UserRequest("updated", "pass", "email", false);
        when(userRepository.findById(id)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> userService.update(id, request));
    }

    @Test
    void update_usernameConflict_throwsResourceAlreadyExistsException() {
        Long id = 1L;
        UserRequest request = new UserRequest("conflicting", null, null, null);
        User existing = createMockUser(id);
        when(userRepository.findById(id)).thenReturn(Optional.of(existing));
        when(userRepository.existsByUsername("conflicting")).thenReturn(true);

        assertThrows(ResourceAlreadyExistsException.class, () -> userService.update(id, request));
    }

    @Test
    void delete_userExists_deletesUser() {
        Long id = 1L;
        User user = createMockUser(id);
        when(userRepository.findById(id)).thenReturn(Optional.of(user));

        userService.delete(id);

        verify(userRepository).delete(user); // Exposes bug: prod calls delete but logs before, verify passes but check impl
    }

    @Test
    void delete_userNotFound_throwsResourceNotFoundException() {
        Long id = 999L;
        when(userRepository.findById(id)).thenReturn(Optional.empty());

        assertThrows(ResourceNotFoundException.class, () -> userService.delete(id));
    }

    @Test
    void checkLogin_validCredentials_returnsLoginResponse() {
        LoginRequest request = new LoginRequest("user1", "correctpass");
        User user = createMockUser(1L);
        user.setPassword("$2a$10$hashedcorrect");
        when(userRepository.findByUsername("user1")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("correctpass", "$2a$10$hashedcorrect")).thenReturn(true);

        LoginResponse result = userService.checkLogin(request);

        assertNotNull(result.token());
    }

    @Test
    void checkLogin_nonExistentUser_throwsUnauthorizedException() {
        LoginRequest request = new LoginRequest("nonexistent", "pass");
        when(userRepository.findByUsername("nonexistent")).thenReturn(Optional.empty());

        assertThrows(UnauthorizedException.class, () -> userService.checkLogin(request));
    }

    @Test
    void checkLogin_invalidPassword_throwsUnauthorizedException() {
        LoginRequest request = new LoginRequest("user1", "wrongpass");
        User user = createMockUser(1L);
        when(userRepository.findByUsername("user1")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("wrongpass", anyString())).thenReturn(false);

        assertThrows(UnauthorizedException.class, () -> userService.checkLogin(request));
    }

    @Test
    void checkLogin_nullUsername_throwsNullPointerException() {
        LoginRequest request = new LoginRequest(null, "pass");

        assertThrows(NullPointerException.class, () -> userService.checkLogin(request));
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