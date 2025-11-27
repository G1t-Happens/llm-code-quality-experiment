package java.com.llmquality.baseline.mapper;

import com.llmquality.baseline.dto.AddressRequest;
import com.llmquality.baseline.dto.AddressResponse;
import com.llmquality.baseline.entity.Address;
import com.llmquality.baseline.entity.User;
import com.llmquality.baseline.enums.AddressType;
import com.llmquality.baseline.mapper.AddressMapper;
import org.junit.jupiter.api.Test;
import org.mapstruct.factory.Mappers;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class AddressMapperTest {

    private final AddressMapper mapper = Mappers.getMapper(AddressMapper.class);

    @Test
    void toAddressEntity_createsNewAddressFromRequestAndUser() {
        User user = new User();
        user.setId(1L);
        AddressRequest request = new AddressRequest("street", "10", "12345", "City", "Country", AddressType.PRIVATE);

        Address result = mapper.toAddressEntity(request, user);

        assertNull(result.getId());
        assertEquals(user, result.getUser());
        assertEquals("street", result.getStreet());
        assertEquals("10", result.getHouseNumber());
        assertEquals("12345", result.getPostalCode());
        assertEquals("City", result.getCity());
        assertEquals("Country", result.getCountry());
        assertEquals(AddressType.PRIVATE, result.getAddressType());
    }

    @Test
    void toAddressResponse_mapsEntityToResponse() {
        Address address = new Address();
        address.setId(2L);
        User user = new User();
        user.setId(1L);
        address.setUser(user);
        address.setStreet("street");
        address.setHouseNumber("10");
        address.setPostalCode("12345");
        address.setCity("City");
        address.setCountry("Country");
        address.setAddressType(AddressType.PRIVATE);

        AddressResponse result = mapper.toAddressResponse(address);

        assertEquals(2L, result.id());
        assertEquals(1L, result.userId());
        assertEquals("street", result.street());
        assertEquals("10", result.houseNumber());
        assertEquals("12345", result.postalCode());
        assertEquals("City", result.city());
        assertEquals("Country", result.country());
        assertEquals(AddressType.PRIVATE, result.addressType());
    }

    @Test
    void updateAddressEntityFromAddressRequest_nullRequest_ignoresAll() {
        Address existing = new Address();
        existing.setStreet("old");

        Address result = mapper.updateAddressEntityFromAddressRequest(null, existing);

        assertEquals("old", result.getStreet());
    }
}