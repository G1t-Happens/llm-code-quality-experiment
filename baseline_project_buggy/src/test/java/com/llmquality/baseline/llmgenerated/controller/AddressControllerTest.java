package com.llmquality.baseline.llmgenerated.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.llmquality.baseline.controller.AddressController;
import com.llmquality.baseline.dto.AddressRequest;
import com.llmquality.baseline.dto.AddressResponse;
import com.llmquality.baseline.service.interfaces.AddressService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(AddressController.class)
class AddressControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AddressService addressService;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    @WithMockUser(roles = "ADMIN")
    void listAll_returnsPagedAddresses() throws Exception {
        mockMvc.perform(get("/api/v1/users/1/addresses"))
                .andExpect(status().isOk());
    }

    @Test
    @WithMockUser(username = "1")
    void create_ownerAccess_returnsCreatedAddress() throws Exception {
        AddressRequest request = new AddressRequest("street", "10", "12345", "city", "country", null);
        AddressResponse response = new AddressResponse(1L, "street", "10", "12345", "city", "country", null, 1L);

        mockMvc.perform(post("/api/v1/users/1/addresses")
                        .contentType(MediaType.TEXT_PLAIN) // Exposes bug: consumes text/plain but JSON body?
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());
    }

    @Test
    void create_invalidCreateGroup_returns400() throws Exception {
        AddressRequest invalid = new AddressRequest("", "10", "12345", "city", "country", null); // blank street

        mockMvc.perform(post("/api/v1/users/1/addresses")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(invalid)))
                .andExpect(status().isBadRequest());
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    void update_validationUpdateGroup_returnsUpdated() throws Exception {
        AddressRequest updateReq = new AddressRequest(null, null, "", null, null, null); // empty pc ok for update?

        mockMvc.perform(patch("/api/v1/users/1/addresses/2")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updateReq)))
                .andExpect(status().isOk());
    }

    @Test
    void getById_notOwner_failsPreAuthorize() throws Exception {
        mockMvc.perform(get("/api/v1/users/999/addresses/1"))
                .andExpect(status().isForbidden());
    }
}