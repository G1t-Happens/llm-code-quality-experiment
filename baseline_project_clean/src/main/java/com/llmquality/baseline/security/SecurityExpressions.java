package com.llmquality.baseline.security;

import com.llmquality.baseline.enums.Role;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;


/**
 * Custom Spring Security expressions for method security.
 * <p>
 * Registered as Spring bean with name "sec" → usable in @PreAuthorize as @sec.xxx()
 * This is the official and recommended way to keep @PreAuthorize expressions clean and testable.
 * </p>
 */
@Component("sec")
public class SecurityExpressions {

    public boolean isOwner(Long resourceOwnerId, Authentication auth) {
        return resourceOwnerId != null
                && auth != null
                && auth.getName() != null
                && resourceOwnerId.toString().equals(auth.getName());
    }

    public boolean canSetAdminFlag(Boolean newValue, Authentication auth) {
        return newValue == null || !newValue || isAdmin(auth);
    }

    public boolean isAdmin(Authentication auth) {
        if (auth == null || auth.getAuthorities() == null) return false;
        return auth.getAuthorities().stream()
                .anyMatch(granted -> Role.ADMIN.authority().equals(granted.getAuthority()));
    }
}
