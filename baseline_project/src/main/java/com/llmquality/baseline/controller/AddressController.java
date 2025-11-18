package com.llmquality.baseline.controller;

import com.llmquality.baseline.dto.AddressRequest;
import com.llmquality.baseline.dto.AddressResponse;
import com.llmquality.baseline.dto.PagedResponse;
import com.llmquality.baseline.service.interfaces.AddressService;
import org.springframework.data.domain.Pageable;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import static com.llmquality.baseline.dto.validation.AddressValidationGroups.*;


@RestController
@RequestMapping("${api.base-path}/users/{userId}/addresses")
public class AddressController {

    private final AddressService addressService;

    public AddressController(AddressService addressService) {
        this.addressService = addressService;
    }


    @GetMapping
    @PreAuthorize("@sec.isAdmin(authentication) or @sec.isOwner(#userId, authentication)")
    public PagedResponse<AddressResponse> listAll(@PathVariable Long userId, Pageable pageable) {
        return addressService.listAll(userId, pageable);
    }

    @GetMapping("/{addressId}")
    @PreAuthorize("@sec.isAdmin(authentication) or @sec.isOwner(#userId, authentication)")
    public AddressResponse getById(@PathVariable Long userId, @PathVariable Long addressId) {
        return addressService.getById(userId, addressId);
    }

    @PostMapping
    @PreAuthorize("@sec.isAdmin(authentication) or @sec.isOwner(#userId, authentication)")
    public AddressResponse create(@PathVariable Long userId, @RequestBody @Validated(Create.class) AddressRequest addressRequest) {
        return addressService.save(userId, addressRequest);
    }

    @PatchMapping("/{addressId}")
    @PreAuthorize("@sec.isAdmin(authentication) or @sec.isOwner(#userId, authentication)")
    public AddressResponse update(@PathVariable Long userId, @PathVariable Long addressId, @RequestBody @Validated(Update.class) AddressRequest addressRequest) {
        return addressService.update(userId, addressId, addressRequest);
    }

    @DeleteMapping("/{addressId}")
    @PreAuthorize("@sec.isAdmin(authentication) or @sec.isOwner(#userId, authentication)")
    public void delete(@PathVariable Long userId, @PathVariable Long addressId) {
        addressService.delete(userId, addressId);
    }
}
