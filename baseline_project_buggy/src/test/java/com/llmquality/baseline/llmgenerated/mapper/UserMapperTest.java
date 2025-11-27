package com.llmquality.baseline.llmgenerated.mapper;

import com.llmquality.baseline.dto.UserRequest;
import com.llmquality.baseline.dto.UserResponse;
import com.llmquality.baseline.entity.User;
import com.llmquality.baseline.mapper.UserMapper;
import org.junit.jupiter.api.Test;
import org.mapstruct.factory.Mappers;
import org.springframework.security.crypto.password.PasswordEncoder;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class UserMapperTest {

    private final UserMapper mapper = Mappers.getMapper(UserMapper.class);

    @Test
    void toUserEntity_createsNewUserWithHashedPassword() {
        PasswordEncoder encoder = mock(PasswordEncoder.class);
        when(encoder.encode("Password1a")).thenReturn("hashed");
        UserRequest request = new UserRequest("newuser", "Password1a", "new@example.com", true);

        User result = mapper.toUserEntity(request, encoder);

        assertNull(result.getId());
        assertEquals("newuser", result.getUsername());
        assertEquals("hashed", result.getPassword());
        assertEquals("new@example.com", result.getEmail());
        assertTrue(result.isAdmin());
    }

    @Test
    void toUserResponse_mapsEntityToResponse() {
        User user = new User();
        user.setId(1L);
        user.setUsername("user1");
        user.setEmail("user1@example.com");
        user.setAdmin(true);

        UserResponse result = mapper.toUserResponse(user);

        assertEquals(1L, result.id());
        assertEquals("user1", result.username());
        assertEquals("user1@example.com", result.email());
        assertTrue(result.admin());
    }

    @Test
    void updateUserEntityFromUserRequest_updatesNonNullFieldsWithHashedPassword() {
        PasswordEncoder encoder = mock(PasswordEncoder.class);
        when(encoder.encode("NewPass1a")).thenReturn("newhashed");
        User existing = new User();
        existing.setId(1L);
        existing.setUsername("olduser");
        existing.setPassword("oldhashed");
        existing.setEmail("old@example.com");
        existing.setAdmin(false);
        UserRequest partial = new UserRequest("newuser", "NewPass1a", null, null);

        User result = mapper.updateUserEntityFromUserRequest(partial, existing, encoder);

        assertEquals(1L, result.getId());
        assertEquals("newuser", result.getUsername());
        assertEquals("newhashed", result.getPassword()); // Exposes bug: double encode in prod expression
        assertEquals("old@example.com", result.getEmail()); // unchanged
        assertFalse(result.isAdmin()); // unchanged
    }

    @Test
    void updateUserEntityFromUserRequest_noPassword_keepsExistingPassword() {
        PasswordEncoder encoder = mock(PasswordEncoder.class);
        User existing = new User();
        existing.setPassword("oldhashed");
        UserRequest partial = new UserRequest(null, null, "new@email.com", true);

        User result = mapper.updateUserEntityFromUserRequest(partial, existing, encoder);

        assertEquals("oldhashed", result.getPassword()); // should keep if null
    }

    @Test
    void updateUserEntityFromUserRequest_nullRequest_ignoresAll() {
        PasswordEncoder encoder = mock(PasswordEncoder.class);
        User existing = new User();
        existing.setUsername("old");

        User result = mapper.updateUserEntityFromUserRequest(null, existing, encoder);

        assertEquals("old", result.getUsername());
    }
}