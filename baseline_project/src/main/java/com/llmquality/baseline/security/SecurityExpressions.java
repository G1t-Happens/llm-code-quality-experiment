package com.llmquality.baseline.security;

import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;

import java.util.Objects;


/**
 * Custom Spring Security expressions for method security.
 * <p>
 * Registered as Spring bean with name "sec" → usable in @PreAuthorize as @sec.xxx()
 * This is the official and recommended way to keep @PreAuthorize expressions clean and testable.
 * </p>
 */
@Component("sec")
public class SecurityExpressions {

    /**
     * Checks if the authenticated user is the owner of the resource.
     * <p>
     * Compares the path variable userId (Long) with the JWT sub claim (String).
     * Uses Objects.equals() for proper null-safety.
     * </p>
     *
     * @param resourceOwnerId the ID from the path variable (e.g. #userId)
     * @param authentication  the current authentication object
     * @return true if the authenticated user owns the resource
     */
    public boolean isOwner(Long resourceOwnerId, Authentication authentication) {
        if (resourceOwnerId == null || authentication == null || authentication.getName() == null) {
            return false;
        }
        return Objects.equals(resourceOwnerId.toString(), authentication.getName());
    }

    /**
     * Checks if the provided {@link Authentication} object represents an admin user.
     * This method verifies if the user has the role 'ROLE_ADMIN' in their granted authorities.
     *
     * @param authentication the {@link Authentication} object representing the current user's authentication details
     * @return {@code true} if the user has the 'ROLE_ADMIN' authority, {@code false} otherwise
     */
    public boolean isAdmin(Authentication authentication) {
        return authentication.getAuthorities().stream()
                .anyMatch(a -> "ROLE_ADMIN".equals(a.getAuthority()));
    }
}
