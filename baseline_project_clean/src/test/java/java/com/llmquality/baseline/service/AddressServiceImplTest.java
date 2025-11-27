package java.com.llmquality.baseline.service;

import com.llmquality.baseline.dto.AddressRequest;
import com.llmquality.baseline.enums.AddressType;
import com.llmquality.baseline.mapper.AddressMapper;
import com.llmquality.baseline.repository.AddressRepository;
import com.llmquality.baseline.repository.UserRepository;
import com.llmquality.baseline.service.AddressServiceImpl;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import static org.junit.jupiter.api.Assertions.assertThrows;

class AddressServiceImplTest {

    @Mock
    private AddressRepository addressRepository;

    @Mock
    private UserRepository userRepository;

    @Mock
    private AddressMapper addressMapper;

    @InjectMocks
    private AddressServiceImpl addressService;


    @Test
    void listAll_nullUserId_throwsNullPointerException() {
        Pageable pageable = PageRequest.of(0, 10);

        assertThrows(NullPointerException.class, () -> addressService.listAll(null, pageable));
    }

    @Test
    void getById_nullUserId_throwsNullPointerException() {
        Long addressId = 2L;

        assertThrows(NullPointerException.class, () -> addressService.getById(null, addressId));
    }

    @Test
    void save_nullUserId_throwsNullPointerException() {
        AddressRequest request = new AddressRequest("street", "10", "12345", "city", "country", AddressType.PRIVATE);

        assertThrows(NullPointerException.class, () -> addressService.save(null, request));
    }

}