package com.llmquality.baseline.security;

import com.llmquality.baseline.repository.AddressRepository;
import org.springframework.beans.factory.annotation.Autowired;
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

    private final AddressRepository addressRepository;

    @Autowired
    public SecurityExpressions(AddressRepository addressRepository) {
        this.addressRepository = addressRepository;
    }

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

    /**
     * Allows setting the {@code admin} flag to {@code true} only for users with ROLE_ADMIN.
     * Used in @PreAuthorize to prevent self-promotion.
     *
     * @param newAdminValue  the new admin value from request (maybe null)
     * @param authentication current authentication
     * @return true if allowed
     */
    public boolean canSetAdminFlag(Boolean newAdminValue, Authentication authentication) {
        return newAdminValue == null || !newAdminValue || isAdmin(authentication);
    }

    /**
     * Returns {@code true} if the current user is either an admin or the actual owner of the requested address.
     * <p>
     * Checks:
     * <ul>
     *   <li>User has {@code ROLE_ADMIN}</li>
     *   <li>Path {@code userId} matches the authenticated user (JWT sub claim)</li>
     *   <li>Address with {@code addressId} exists and belongs to {@code userId}</li>
     * </ul>
     * </p>
     * Provides full IDOR protection for {@code /users/{userId}/addresses/{addressId}} endpoints.
     * Non-existent or foreign addresses yield {@code false} without leaking existence.
     *
     * @param userId         user ID from path ({@code #userId})
     * @param addressId      address ID from path ({@code #addressId})
     * @param authentication current authentication (never {@code null} in {@code @PreAuthorize})
     * @return {@code true} if access is allowed
     */
    public boolean isOwnerOfAddress(Long userId, Long addressId, Authentication authentication) {
        return isAdmin(authentication)
                || (userId != null
                && addressId != null
                && userId.toString().equals(authentication.getName())
                && addressRepository.existsByIdAndUserId(addressId, userId));
    }
}
