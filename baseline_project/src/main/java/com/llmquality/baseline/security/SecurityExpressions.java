package com.llmquality.baseline.security;

import com.llmquality.baseline.enums.Role;
import com.llmquality.baseline.repository.AddressRepository;
import org.springframework.beans.factory.annotation.Autowired;
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

    private final AddressRepository addressRepository;

    @Autowired
    public SecurityExpressions(AddressRepository addressRepository) {
        this.addressRepository = addressRepository;
    }

    public boolean isOwner(Long resourceOwnerId, Authentication auth) {
        return resourceOwnerId != null
                && resourceOwnerId.toString().equals(auth.getName());
    }

    public boolean isOwnerOfAddress(Long userId, Long addressId, Authentication auth) {
        return isAdmin(auth)
                || (userId != null && isOwner(userId, auth)
                && addressRepository.existsByIdAndUserId(addressId, userId));
    }

    public boolean canSetAdminFlag(Boolean newValue, Authentication auth) {
        return newValue == null || !newValue || isAdmin(auth);
    }

    public boolean isAdmin(Authentication auth) {
        return auth.getAuthorities().stream()
                .anyMatch(granted -> Role.ADMIN.authority().equals(granted.getAuthority()));
    }
}
