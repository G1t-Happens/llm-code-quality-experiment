package com.llmquality.baseline.security;

import com.llmquality.baseline.enums.Role;
import com.llmquality.baseline.exception.ForbiddenAccessException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Component;

@Component
public class AuthenticationFacade {

    /**
     * Gibt die aktuelle Authentication zurück.
     * @return die Authentication des aktuellen Benutzers
     */
    public Authentication getAuthentication() {
        return SecurityContextHolder.getContext().getAuthentication();
    }


    public Long getCurrentUserId() {
        Authentication authentication = getAuthentication();

        if (authentication == null || !authentication.isAuthenticated()) {
            throw new SecurityException("No valid authentication found");
        }

        if (!(authentication.getPrincipal() instanceof Jwt jwt)) {
            throw new SecurityException("Expected JWT token, but got: " +
                    (authentication.getPrincipal() == null ? "null" : authentication.getPrincipal().getClass()));
        }

        if (!jwt.hasClaim("userId")) {
            throw new SecurityException("JWT token does not contain 'userId' claim");
        }

        Long userId = jwt.getClaim("userId");
        if (userId == null) {
            throw new ForbiddenAccessException("User", "userId claim", "missing");
        }
        return userId;
    }


    public boolean isAdmin() {
        final Authentication authentication = getAuthentication();
        boolean isAdmin = authentication.getAuthorities().stream()
                .anyMatch(authority -> authority.getAuthority().equals(Role.ADMIN.getName()));
        return isAdmin;
    }
}
